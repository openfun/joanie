"""
Utils to compare generated document for testing.
Allows to compare when a library upgrade to newer version changes the layout of
a validated design of documents.
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pymupdf
from PIL import Image, ImageChops, ImageStat

from joanie.core.utils import issuers


def call_issuers_generate_document(
    name: str, context: dict, path: str, creation_date=False
):
    """
    Call generate document from issuers but add extra step to output the file
    for testing purposes.
    """
    if creation_date:
        context["creation_date"] = datetime(2025, 11, 18, 14, tzinfo=ZoneInfo("UTC"))

    pdf_bytes = issuers.generate_document(name, context)
    pdf_output_path = path + name + ".pdf"
    with open(pdf_output_path, "wb") as pdf_file:
        pdf_file.write(pdf_bytes)
    return pdf_output_path


def convert_pdf_to_png(pdf_path: str):
    """
    Convert the first page of a PDF file into a PNG image at 150 DPI.
    Returns the path to the generated image.
    """
    generated_pdf = pymupdf.open(pdf_path)
    generated_pdf = generated_pdf.load_page(0)
    generated_image = generated_pdf.get_pixmap(dpi=150)
    generated_image_path = pdf_path.replace(".pdf", ".png")
    generated_image.save(generated_image_path)
    return generated_image_path


def compare_images(first_image: Image, second_image: Image, output_path: str):
    """
    Compare two images and save the difference image to the specified output path.
    Returns the average RMS difference between the images.
    """
    diff = ImageChops.difference(first_image, second_image)
    diff.save(output_path)
    rms = ImageStat.Stat(diff).rms
    tolerated_diff = sum(rms) / len(rms)
    return tolerated_diff


def clear_generated_files(base_path: str, file_name: str):
    """
    Remove the generated files from the output directory.
    """
    os.remove(base_path + file_name + ".png")
    os.remove(base_path + file_name + "_diff.png")
