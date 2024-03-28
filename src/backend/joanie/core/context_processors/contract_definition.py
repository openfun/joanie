"""Context processors for contract definition."""

from joanie.core.utils.contract_context_processors import parse_richie_syllabus


def richie_syllabus(context):
    """
    This processor is in charge to retrieve/parse syllabus RDF attributes
    from a remote Richie instance.
    """
    course_code = context["course"]["code"]
    contract_language = context["contract"]["language"]

    return {"syllabus": parse_richie_syllabus(course_code, contract_language)}
