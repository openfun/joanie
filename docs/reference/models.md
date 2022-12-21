# Models

Here are described some important relations between our models.
You can also take a look at [core models](https://github.com/openfun/joanie/tree/main/src/backend/joanie/core/models)
and [payment models](https://github.com/openfun/joanie/tree/main/src/backend/joanie/payment/models.py).

## Relations between `User` / `Organization` / `Order` / `Product` / `Course` / `Course Run` and `Enrollment` models

```mermaid
erDiagram

    %% Models
        User {
            Integer id PK
        }
        Organization {
            Integer id PK
        }
        Enrollment {
            User user_id FK
            CourseRun course_run_id FK
        }
        Order {
            Integer id PK
            User owner FK
            Course course FK
            OrderTargetCourseRelation target_courses FK
        }
        CourseRun {
            string resource_link PK
        }
        Course {
            string code PK 
        }
        Product {
            Integer id PK
            Course course FK
            ProductTargetCourseRelation target_courses FK
        }
        
        ProductTargetCourseRelation {
            Product product FK
            Course course FK
            PositiveSmallInteger position
            Boolean is_graded
            CourseRun course_runs FK
        }
        
        OrderTargetCourseRelation {
            Order order FK
            Course course FK
            PositiveSmallInteger position
            Boolean is_graded
            CourseRun course_runs FK
        }
        
    
    %% Relations
        User ||--o{ Enrollment : "has"
        User ||--o{ Order: "owns"
        
        Enrollment }o--|| CourseRun : "is"
        
        Order }o--|| Course : ""
        Order }o--|| Organization : "sells"
        Order }o--|| Product : ""
        Order ||--o{ OrderTargetCourseRelation : ""
        
        CourseRun }o--|| Course : ""
        CourseRun }o--o{ OrderTargetCourseRelation : "" 
        CourseRun }o--|| on_add_course_runs_to_product_course_relation : ""
        on_add_course_runs_to_product_course_relation || -- o{ ProductTargetCourseRelation : ""
        
        Course }o--o{ Organization : "authors"
        Course }o--o{ Product : "displays"
        Course ||--o{ OrderTargetCourseRelation : "is included in"
        Course ||--o{ ProductTargetCourseRelation : "is included in"

        Product }o--o{ Organization : "promotes"
        Product ||--o{ ProductTargetCourseRelation : ""
        
        ProductTargetCourseRelation ||..|| OrderTargetCourseRelation : "copied at order creation"
```

### Focus

#### `course` and `target_courses` fields of `Product` and `Order` models

The `course` field represents the course under which the product is sold. Each order generated when
this product is sold will also be related to it. On the other hand, the `target_courses` field
represents the courses that the students will be able to follow once they buy the product.

#### The `ProductTargetCourseRelation` and `OrderTargetCourseRelation` models

First the `ProductTargetCourseRelation` model is a join table between  a `Product` and a `Course`.

It has extra attributes :
- `position`: To order courses in the product
- `is_graded`: To take in account the grade of the course for the certificate delivery
- `course_runs`: To restrict the course to specific course runs. If this field is left blank, all 
  course runs related to linked course will be eligible for enrollment.

Then the `OrderTargetCourseRelation` model is a join table between an `Order` and a `Course`.
This relation is created at the creation of an `Order` by copying the `CourseProductRelation`
of the related `Product`. In this way, a `Product` can be updated without impacting previously
created `Order`.

#### The signal `on_add_course_runs_to_product_course_relation`

It corresponds to a `m2m_changed` signal that is fired before a course run is added to a
product course relation. It is in charge of preventing the addition of a course run to a product
course relation if those two resources are not related to the same course.


## Relation between `Order` / `Invoice` and `Transaction` models

```mermaid
erDiagram
    %% Models
    Order {
        Integer id PK
        User owner FK
        Course course FK
    }

    Invoice {
        Integer id PK
        Order order FK
        Invoice parent FK
    }
    
    Transaction {
        Integer id PK
        Invoice invoice FK
    }
    
    %% Relations
    Order ||--|| only_one_invoice_without_parent_per_order : ""
    only_one_invoice_without_parent_per_order ||--o{ Invoice : "has"
    
    Invoice ||--o{ Invoice : "is child of"
    Invoice ||--o{ Transaction : "reconcils"
```

### Focus

#### Nesting of `Invoice`

The `Invoice` model has a field `parent` to be able to link invoices between them.
An `Order` should have only one invoice without parent which is the main invoice. If we
need to refund the client, invoices with a negative amount (a credit notes) are created
which are children of the main invoice.

#### Constraints on `Invoice` model

The `Invoice` model has two database constraints :

- A `UniqueConstraint` "only_one_invoice_without_parent_per_order" to prevent an order from 
having several main invoices.

- A `CheckConstraint` "main_invoice_should_have_a_positive_amount" to ensure that a
main invoice has a positive amount.

## Relation between `Order` / `Product` / `CertificateDefinition` and `Certificate` models

```mermaid
erDiagram
    %% Models
    Product
    CertificateDefinition
    User
    Order
    Certificate
    
    %% Relations
    Product }o--o| CertificateDefinition : ""
    Product || -- o{ Order : ""
    CertificateDefinition ||--o{ Certificate : "is defined by"
    
    User ||--o{ Order : "owns"
    Order }o--o| Certificate : ""
```

### Focus

#### `Product` / `CertificateDefinition` constraint

Only `Product` of type `CREDENTIAL` or `CERTIFICATE` can have a `CertificateDefinition`.
