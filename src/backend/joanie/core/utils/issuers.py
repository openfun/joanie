"""Utils that can be useful throughout Joanie's core app for document issuers"""

from pathlib import Path

from django.template import Context
from django.template.engine import Engine
from django.template.loader import get_template

from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration


def generate_document(name: str, context: dict) -> bytes:
    """
    Generate the document with a given path and the instance
    of an object we would like to retrieve data from.
    Note:
        - The path will help us in finding the correct .html and
        .css file for the document in the app directory.
        Make sure that those files exist in the 'templates' folder.
        - If the context is equal to 'None' or is an empty '{}', it
        will render the document without the context data.
    """
    html_template_path = Path(f"issuers/{name}.html")
    css_template_name = Path(f"issuers/{name}.css")

    doc_html = HTML(
        string=Engine.get_default()
        .get_template(html_template_path)
        .render(Context(context))
    )
    font_config = FontConfiguration()
    css = CSS(
        string=get_template(css_template_name).render(context),
        font_config=font_config,
    )
    return doc_html.write_pdf(stylesheets=[css], zoom=1, font_config=font_config)
