# Models

Here are described some important relations in our models.

## Relations 

```mermaid
erDiagram

PreCourse_attestation_teachers{

AutoField id

}

PreCourse{

UUIDField id

DateTimeField created_on

DateTimeField updated_on

DateField submission_date

CharField title

CharField status

PositiveIntegerField session

PositiveIntegerField diffusion

DateField enrollment_start_date

DateField course_start_date

DateField course_end_date

DateField enrollment_end_date

CharField kind

PositiveIntegerField student_number

CharField plaform

CharField membership_level

BooleanField double_display

TextField summary

TextField contacts

TextField email_addresses

TextField phone_numbers

PositiveIntegerField week_duration

PositiveIntegerField estimated_weekly_hours

TextField comment

BooleanField attestation

CharField test_attestation

DateField estimated_attestation_generation_date

DateField attestation_generation_date

TextField attestation_comment

PositiveIntegerField delivered_attestation_quantity

PositiveIntegerField registered_quantity

BooleanField certificate

CharField certificate_type

DateField exam_start_date

DateField exam_end_date

DateField payment_start_date

DateField payment_end_date

DurationField exam_duration

PositiveIntegerField exam_price

DateField certificate_generation_date

PositiveIntegerField delivered_certificate_quantity

CharField exam_url

TextField certificate_comment

TextField invoicing

CharField invoice_reference

TextField invoicing_comment

CharField cohort_invoicing

CharField member_invoicing

CharField partner_invoicing

PositiveIntegerField invoicing_year

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

PreCourse_attestation_teachers||--|{PreCourse : precourse

PreCourse_attestation_teachers||--|{User : user

PreCourse||--|{User : manager

PreCourse||--|{Organization : organization_member

PreCourse||--|{Organization : organization_lead

PreCourse||--|{Organization : organization_producer

PreCourse||--|{Organization : secondary_organization

PreCourse}|--|{User : attestation_teachers

PricingFPCbyOrg||--|{Pricing : pricing

Contract||--|{Organization : organization

Contract||--|{Pricing : pricing

Transaction||--|{Contract : contract

Transaction||--|{PreCourse : precourse

Quote||--|{Organization : organization

QuoteLine||--|{Quote : quote

Invoice||--|{Organization : organization

InvoiceLine||--|{Invoice : invoice

User||--|{Course : course

User}|--|{PreCourse : attestation_teacher_precourses

User}|--|{Organization : teaches_in

Organization}|--|{User : teachers

Organization}|--|{Course : courses

Organization||--|{User : representative_user

Organization||--|{Organization : parent

Course||--|{User : lead_teacher

Course}|--|{Organization : organizations

```
