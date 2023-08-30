# Setup Moodle backend

In order to use Moodle as an LMS backend in Joanie,
we need to set up a Moodle webservice, and a Moodle webservice client.

## Setup Moodle webservice

### Create a Joanie user

1. In the Moodle admin panel, go to `Site administration > Users > Accounts > Add a new user`.

    ![Moodle admin : add a new user](assets/moodle_add_new_user_1.png)

2. Fill the form with the following values:

   - Username: `joanie`
   - Password: `xxxxxxxx`
   - First name: `joanie`
   - Last name: `joanie`
   - Email address: `joanie@example.com`

   ![Moodle admin : new user values](assets/moodle_add_new_user_2.png)

3. Click on the **Create user** button.

### Assign manager role to Joanie user

1. In the Moodle admin panel, go to `Site administration > Users > Permissions > Assign system roles`.

    ![Moodle admin : navigate to assign system role](assets/moodle_assign_system_role_1.png)

2. Click on the existing **Manager** role.

    ![Moodle admin : assign manager role](assets/moodle_assign_system_role_2.png)

3. In the **Potential users** list, select the **joanie** user, and click on the **Add** button.

    ![Moodle admin : assign manager role to user](assets/moodle_assign_system_role_3.png)

### Create a Joanie webservice

[Detailed Moodle configuration documentation](https://docs.moodle.org/402/en/Using_web_services)


1. In the Moodle admin panel, go to `Site administration > Server > Web services > External services`.

    ![Moodle admin : navigate to external services](assets/moodle_add_external_webservice_1.png)

2. Click on the **Add** button.
 
    ![Moodle admin : add external services](assets/moodle_add_external_webservice_2.png)

3. Fill the form with the following values:

   - Name: `Joanie`
   - Shortname: `joanie`
   - Enabled: `checked`
   - Authorized users only: `checked`

    ![Moodle admin : external services values](assets/moodle_add_external_webservice_3.png)

4. Click on the **Add service** button.

5. Click on the **Add functions** button.

    ![Moodle admin : navigate to external services add functions](assets/moodle_add_external_webservice_functions_1.png)

6. For each function below, search for it in the dropdown select, and click it.

   - core_course_get_courses
   - core_enrol_get_enrolled_users
   - core_webservice_get_site_info
   - enrol_manual_enrol_users
   - enrol_manual_unenrol_users
   - gradereport_user_get_grade_items

7. Click on the **Add functions** button.

    ![Moodle admin : external services add functions](assets/moodle_add_external_webservice_functions_2.png)

8. In the Moodle admin panel, go to `Site administration > Server > Web services > External services`.
    Click on the **Authorized users** in the **Joanie** line.

    ![Moodle admin : navigate to external services authorized users](assets/moodle_add_external_webservice_authorized_users_1.png)

9. In the **Not authorized users ** list, select the **joanie** user, and click on the **Add** button.

    ![Moodle admin : external services add authorized user](assets/moodle_add_external_webservice_authorized_users_2.png)

## Setup Moodle webservice client

A python library exists to interact with Moodle webservices: [moodlepy](https://github.com/hexatester/moodlepy).

### Install moodlepy

```bash
pip install moodlepy
```

### Set moodle as an LMS backend in Joanie

_**TODO**_
