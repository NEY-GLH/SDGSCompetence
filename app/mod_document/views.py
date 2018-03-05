import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
import inspect
import json
import os
import time
from docx import Document
from flask import Blueprint, jsonify
from flask_table import Table, Col
from sqlalchemy import and_, or_, case
from flask import render_template, request, url_for, redirect, Blueprint, send_from_directory
from flask.ext.login import login_required, current_user
from app.views import admin_permission
from app.models import *
from app.competence import s
from app.qpulseweb import QPulseWeb
from app.qpulse_details import QpulseDetails
from forms import *
from sqlalchemy.orm import aliased

document = Blueprint('document', __name__, template_folder='templates')

# queries
def get_doc_info(c_id):
    """
    Method to get doc infor from database

    :param c_id: ID of competence to be returned
    :type c_id: INT
    :return:
    """
    print('query')
    competence_list = s.query(Competence).\
        join(CompetenceDetails).\
        join(Users, CompetenceDetails.creator_rel). \
        filter(Competence.id == c_id).\
        values(CompetenceDetails.title,
               CompetenceDetails.qpulsenum,
               CompetenceDetails.scope,
               (Users.first_name + ' ' + Users.last_name).label('name'),
               Competence.current_version)
    for c in competence_list:
        return c

def get_subsections(c_id):
    """
    Method to get section and subsection info from database
    :param c_id: ID of competence to be returned
    :type c_id: INT
    :return:
    """
    subsections = s.query(Subsection). \
        join(Section). \
        join(Competence).\
        filter(Subsection.c_id == c_id). \
        values(Subsection.name.label('subsec_name'),
               Subsection.comments,
               Section.name.label('sec_name'),
               Section.id,
               Section.constant,
               Subsection.evidence)
    subsection_list = []
    for i in subsections:
        subsection_list.append(i)
    return subsection_list

def get_qpulsenums(c_id):
    qpulse_no_list = s.query(Documents).\
        filter(Documents.c_id == c_id).\
        values(Documents.qpulse_no)
    doc_list = []
    for i in qpulse_no_list:
        doc_list.append(i)
    return doc_list

# evidence query - would this need to be filtered for each sub section - leave until Natalie has finished

# def get_evidence(c_id)
#     evidence = s.query(). \
#         join(Subsection). \
#         join(Assessments). \
#         join(Users)
#     filter(Subsection.c_id == c_id)
#     values(Evidence.name,
#            Evidence.s_id,
#
#            )

    return


# methods

def get_page_body(boxes):
    """
    This method is used for creating the header and footer
    :param boxes:
    :return:
    """
    for box in boxes:
        if box.element_tag == 'body':
            return box

        return get_page_body(box.all_children())

def export_document(c_id):
    """
    Method to export a blank competence document to PDF
    :param c_id: ID of competence to be returned
    :type c_id: INT
    :return:
    """
    document = Document()

    # Get variables using queries
    comp = get_doc_info(c_id)
    subsec = get_subsections(c_id)
    qpulse = get_qpulsenums(c_id)

    # Competence details
    title = comp.title
    docid = comp.qpulsenum
    version_no = comp.current_version
    author = comp.name
    scope = comp.scope

    # subsection details
    subsec_dict = {}

    for sub in subsec:
        sub_name = sub.subsec_name
        sec_name = sub.sec_name
        comments = sub.comments
        constant = sub.constant
        sub_id = sub.id
        value_list = [sub_name, comments, constant, sub_id]
        subsec_dict[sec_name]= value_list

    #associated qpulse documents
    qpulse_list = {}

    for qpulse_no in qpulse:
        d = QpulseDetails()
        details = d.Details()
        username = str(details[1])
        password = str(details[0])
        qpulse_name = QPulseWeb().get_doc_by_id(username, password, qpulse_no)
        qpulse_list[qpulse_no]=qpulse_name

    # evidence

    evidence_list = {}



    print('***Rendering main document***')
    # Make main document
    html_out = render_template('export_to_pdf.html', title=title, scope=scope, docid=docid ,version_no=version_no, author=author, subsec_dict=subsec_dict, qpulse_list=qpulse_list)
    html = HTML(string=html_out)

    main_doc = html.render(stylesheets=[CSS('static/css/simple_report.css')])

    exists_links = False

    # Add headers and footers
    # header = html.render(stylesheets=[CSS(string='div {position: fixed; top: 1cm; left: 1cm;}')])
    header_out = render_template('header.html', title=title, docid=docid)
    header_html = HTML(string=header_out)
    header = header_html.render(stylesheets=[CSS('static/css/simple_report.css'), CSS(string='div {position: fixed; top: -2.7cm; left: 0cm;}')])

    header_page = header.pages[0]
    exists_links = exists_links or header_page.links
    header_body = get_page_body(header_page._page_box.all_children())
    header_body = header_body.copy_with_children(header_body.all_children())

    # Template of footer
    footer_out = render_template('footer.html', version_no=version_no, author=author)
    footer_html = HTML(string=footer_out)
    footer = footer_html.render(stylesheets=[CSS('static/css/simple_report.css'), CSS(string='div {position: fixed; bottom: -2.1cm; left: 0cm;}')])

    footer_page = footer.pages[0]
    exists_links = exists_links or footer_page.links
    footer_body = get_page_body(footer_page._page_box.all_children())
    footer_body = footer_body.copy_with_children(footer_body.all_children())

    # Insert header and footer in main doc
    for i, page in enumerate(main_doc.pages):

        page_body = get_page_body(page._page_box.all_children())
        page_body.children += header_body.all_children()
        page_body.children += footer_body.all_children()

        if exists_links:
            page.links.extend(header_page.links)
            page.links.extend(footer_page.links)

    main_doc.write_pdf(target=app.config["UPLOAD_FOLDER"]+"/test.pdf")
    return html_out

#views
@document.route('/export', methods=['GET', 'POST'])
def export_document_view():
    """
    View to export competence to PDF
    :return:
    """
    print(request.method)
    if request.method == 'GET':
        c_id = request.args.get('c_id')
        print('cid')
        print(c_id)
        html = export_document(c_id)
        uploads = app.config["UPLOAD_FOLDER"]
        return send_from_directory(directory=uploads, filename="test.pdf", as_attachment=True, attachment_filename="competence_download.pdf")