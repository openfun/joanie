"""Module for testing the Open edX models."""
# pylint: disable=protected-access

from django.test import TestCase

from joanie.edx_imports import edx_factories


class OpenEdxModelsTestCase(TestCase):
    """Test case for the Open edX models."""

    def test_edx_models_user_safe_dict(self):
        """Test the safe_dict method of the EdxUser model."""
        edx_user = edx_factories.EdxUserFactory()

        self.assertEqual(
            edx_user.safe_dict(),
            {
                "id": edx_user.id,
                "first_name": edx_user.first_name,
                "last_name": edx_user.last_name,
                "is_staff": edx_user.is_staff,
                "is_active": edx_user.is_active,
                "is_superuser": edx_user.is_superuser,
                "date_joined": edx_user.date_joined,
                "last_login": edx_user.last_login,
            },
        )

    def test_edx_models_user_profile_safe_dict(self):
        """Test the safe_dict method of the EdxUserProfile model."""
        edx_user_profile = edx_factories.EdxUserProfileFactory()

        self.assertEqual(
            edx_user_profile.safe_dict(),
            {
                "id": edx_user_profile.id,
                "user_id": edx_user_profile.user_id,
                "meta": edx_user_profile.meta,
                "courseware": edx_user_profile.courseware,
                "allow_certificate": edx_user_profile.allow_certificate,
                "profile_image_uploaded_at": edx_user_profile.profile_image_uploaded_at,
            },
        )

    def test_edx_models_user_preference_safe_dict(self):
        """Test the safe_dict method of the EdxUserPreference model."""
        edx_user_preference = edx_factories.EdxUserPreferenceFactory()

        self.assertEqual(
            edx_user_preference.safe_dict(),
            {
                "id": edx_user_preference.id,
                "user_id": edx_user_preference.user_id,
                "key": edx_user_preference.key,
                "value": edx_user_preference.value,
            },
        )

    def test_edx_models_course_overview_safe_dict(self):
        """Test the safe_dict method of the EdxCourseOverview model."""
        edx_course_overview = edx_factories.EdxCourseOverviewFactory()

        self.assertEqual(
            edx_course_overview.safe_dict(),
            {
                "id": edx_course_overview.id,
                "_location": edx_course_overview._location,
                "display_number_with_default": edx_course_overview.display_number_with_default,
                "display_org_with_default": edx_course_overview.display_org_with_default,
                "course_image_url": edx_course_overview.course_image_url,
                "certificates_show_before_end": edx_course_overview.certificates_show_before_end,
                "has_any_active_web_certificate": (
                    edx_course_overview.has_any_active_web_certificate
                ),
                "cert_name_short": edx_course_overview.cert_name_short,
                "cert_name_long": edx_course_overview.cert_name_long,
                "mobile_available": edx_course_overview.mobile_available,
                "visible_to_staff_only": edx_course_overview.visible_to_staff_only,
                "_pre_requisite_courses_json": edx_course_overview._pre_requisite_courses_json,
                "cert_html_view_enabled": edx_course_overview.cert_html_view_enabled,
                "invitation_only": edx_course_overview.invitation_only,
                "created": edx_course_overview.created,
                "modified": edx_course_overview.modified,
                "version": edx_course_overview.version,
                "org": edx_course_overview.org,
                "display_name": edx_course_overview.display_name,
                "start": edx_course_overview.start,
                "end": edx_course_overview.end,
                "advertised_start": edx_course_overview.advertised_start,
                "facebook_url": edx_course_overview.facebook_url,
                "social_sharing_url": edx_course_overview.social_sharing_url,
                "end_of_course_survey_url": edx_course_overview.end_of_course_survey_url,
                "certificates_display_behavior": edx_course_overview.certificates_display_behavior,
                "lowest_passing_grade": edx_course_overview.lowest_passing_grade,
                "days_early_for_beta": edx_course_overview.days_early_for_beta,
                "enrollment_start": edx_course_overview.enrollment_start,
                "enrollment_end": edx_course_overview.enrollment_end,
                "enrollment_domain": edx_course_overview.enrollment_domain,
                "max_student_enrollments_allowed": (
                    edx_course_overview.max_student_enrollments_allowed
                ),
                "announcement": edx_course_overview.announcement,
                "catalog_visibility": edx_course_overview.catalog_visibility,
                "course_video_url": edx_course_overview.course_video_url,
                "effort": edx_course_overview.effort,
                "short_description": edx_course_overview.short_description,
            },
        )

    def test_edx_models_course_safe_dict(self):
        """Test the safe_dict method of the EdxCourse model."""
        edx_course = edx_factories.EdxCourseFactory()

        self.assertEqual(
            edx_course.safe_dict(),
            {
                "id": edx_course.id,
                "key": edx_course.key,
                "level": edx_course.level,
                "score": edx_course.score,
                "is_active": edx_course.is_active,
                "prevent_auto_update": edx_course.prevent_auto_update,
                "modification_date": edx_course.modification_date,
                "title": edx_course.title,
                "short_description": edx_course.short_description,
                "image_url": edx_course.image_url,
                "session_number": edx_course.session_number,
                "university_display_name": edx_course.university_display_name,
                "show_in_catalog": edx_course.show_in_catalog,
                "language": edx_course.language,
                "show_about_page": edx_course.show_about_page,
                "start_date": edx_course.start_date,
                "end_date": edx_course.end_date,
                "thumbnails_info": edx_course.thumbnails_info,
                "enrollment_start_date": edx_course.enrollment_start_date,
                "enrollment_end_date": edx_course.enrollment_end_date,
                "certificate_passing_grade": edx_course.certificate_passing_grade,
            },
        )

    def test_edx_models_universities_safe_dict(self):
        """Test the safe_dict method of the EdxUniversity model."""
        edx_university = edx_factories.EdxUniversityFactory()

        self.assertEqual(
            edx_university.safe_dict(),
            {
                "id": edx_university.id,
                "name": edx_university.name,
                "slug": edx_university.slug,
                "code": edx_university.code,
                "logo": edx_university.logo,
                "description": edx_university.description,
                "detail_page_enabled": edx_university.detail_page_enabled,
                "score": edx_university.score,
                "short_name": edx_university.short_name,
                "is_obsolete": edx_university.is_obsolete,
                "prevent_auto_update": edx_university.prevent_auto_update,
                "partnership_level": edx_university.partnership_level,
                "banner": edx_university.banner,
                "certificate_logo": edx_university.certificate_logo,
            },
        )

    def test_edx_models_course_universitiy_relations_safe_dict(self):
        """Test the safe_dict method of the EdxCourseUniversityRelations model."""
        edx_course_university_relations = (
            edx_factories.EdxCourseUniversityRelationFactory()
        )

        self.assertEqual(
            edx_course_university_relations.safe_dict(),
            {
                "id": edx_course_university_relations.id,
                "university_id": edx_course_university_relations.university_id,
                "course_id": edx_course_university_relations.course_id,
                "order": edx_course_university_relations.order,
            },
        )

    def test_edx_models_course_enrollment_safe_dict(self):
        """Test the safe_dict method of the EdxCourseEnrollment model."""
        edx_enrollment = edx_factories.EdxEnrollmentFactory()

        self.assertEqual(
            edx_enrollment.safe_dict(),
            {
                "id": edx_enrollment.id,
                "user_id": edx_enrollment.user_id,
                "course_id": edx_enrollment.course_id,
                "is_active": edx_enrollment.is_active,
                "mode": edx_enrollment.mode,
                "created": edx_enrollment.created,
            },
        )

    def test_edx_models_generated_certificate_safe_dict(self):
        """Test the safe_dict method of the EdxGeneratedCertificate model."""
        edx_generated_certificate = edx_factories.EdxGeneratedCertificateFactory()

        self.assertEqual(
            edx_generated_certificate.safe_dict(),
            {
                "id": edx_generated_certificate.id,
                "user_id": edx_generated_certificate.user_id,
                "download_url": edx_generated_certificate.download_url,
                "grade": edx_generated_certificate.grade,
                "course_id": edx_generated_certificate.course_id,
                "key": edx_generated_certificate.key,
                "distinction": edx_generated_certificate.distinction,
                "status": edx_generated_certificate.status,
                "verify_uuid": edx_generated_certificate.verify_uuid,
                "download_uuid": edx_generated_certificate.download_uuid,
                "name": edx_generated_certificate.name,
                "created_date": edx_generated_certificate.created_date,
                "modified_date": edx_generated_certificate.modified_date,
                "error_reason": edx_generated_certificate.error_reason,
                "mode": edx_generated_certificate.mode,
            },
        )
