# Models

Here are described some important relations in our models.

## Relations 

```mermaid

erDiagram

CourseSubmission{

UUIDField id

DateTimeField created_on

DateTimeField updated_on

CharField title

DateField start_date

BooleanField double_display

CharField kind

CharField mooc_kind

PositiveIntegerField spoc_learner_quantity

BooleanField spocc_certificate

}

Pricing{

UUIDField id

DateTimeField created_on

DateTimeField updated_on

CharField name

PositiveSmallIntegerField level

DecimalField price

PositiveSmallIntegerField year

PositiveSmallIntegerField course_quantity

BooleanField double_display_included

PositiveSmallIntegerField double_display_unit_price

DecimalField course_over_unit_price

DecimalField course_archived_open_unit_price

DecimalField campus_new_unit_price

DecimalField campus_learner_price

PositiveSmallIntegerField fpc_fun_percent

DecimalField fpc_fun_mini

DecimalField fpc_certificate

}

PricingFPCbyOrg{

UUIDField id

DateTimeField created_on

DateTimeField updated_on

PositiveSmallIntegerField range_start

PositiveSmallIntegerField range_end

DecimalField unit_price

DecimalField minimum

}

Contract{

UUIDField id

DateTimeField created_on

DateTimeField updated_on

DateField start

DateField end

FileField file

}

Transaction{

UUIDField id

DateTimeField created_on

DateTimeField updated_on

PositiveIntegerField debit

PositiveIntegerField credit

}

Quote{

UUIDField id

DateTimeField created_on

DateTimeField updated_on

CharField pep_number

}

QuoteLine{

UUIDField id

DateTimeField created_on

DateTimeField updated_on

TextField label

DecimalField unit_price

DecimalField quantity

}

Invoice{

UUIDField id

DateTimeField created_on

DateTimeField updated_on

CharField pep_number

}

InvoiceLine{

UUIDField id

DateTimeField created_on

DateTimeField updated_on

TextField label

DecimalField unit_price

DecimalField quantity

}

User{

ForeignKey logentry

ForeignKey addresses

ForeignKey orders

ForeignKey enrollments

ForeignKey credit_cards

ForeignKey issued_badges

DateTimeField last_login

BooleanField is_superuser

CharField username

CharField first_name

CharField last_name

CharField email

BooleanField is_staff

BooleanField is_active

DateTimeField date_joined

UUIDField id

DateTimeField created_on

DateTimeField updated_on

CharField language

CharField password

BooleanField is_teacher

FileField signature

ManyToManyField groups

ManyToManyField user_permissions

}

Organization{

TranslationsForeignKey translations

ManyToManyField products

ForeignKey order

UUIDField id

DateTimeField created_on

DateTimeField updated_on

CharField code

FileField logo

}

Course{

TranslationsForeignKey translations

ForeignKey course_runs

ManyToManyField targeted_by_products

ForeignKey product_relations

ForeignKey order

ManyToManyField orders

ForeignKey order_relations

UUIDField id

DateTimeField created_on

DateTimeField updated_on

CharField code

ManyToManyField products

}

CourseSubmission||--|{Transaction : transaction

CourseSubmission||--|{User : user

CourseSubmission||--|{Organization : organization

Pricing||--|{PricingFPCbyOrg : pricingfpcbyorg

Pricing||--|{Contract : contract

PricingFPCbyOrg||--|{Pricing : pricing

Contract||--|{Transaction : transaction

Contract||--|{Organization : organization

Contract||--|{Pricing : pricing

Transaction||--|{Contract : contract

Transaction||--|{CourseSubmission : course_submission

Quote||--|{QuoteLine : quoteline

Quote||--|{Organization : organization

QuoteLine||--|{Quote : quote

Invoice||--|{InvoiceLine : invoiceline

Invoice||--|{Organization : organization

InvoiceLine||--|{Invoice : quote

User||--|{Organization : organization

User||--|{Course : course

User||--|{CourseSubmission : pre_courses

User}|--|{Organization : teaches_in

Organization}|--|{User : teachers

Organization||--|{Organization : organization

Organization}|--|{Course : courses

Organization||--|{CourseSubmission : pre_courses

Organization||--|{Contract : contract

Organization||--|{Quote : quote

Organization||--|{Invoice : invoice

Organization||--|{User : representative_user

Organization||--|{Organization : parent

Course||--|{User : lead_teacher

Course}|--|{Organization : organizations

```
