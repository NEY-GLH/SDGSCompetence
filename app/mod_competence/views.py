from collections import OrderedDict

from flask import Blueprint, jsonify
from flask_table import Table, Col, ButtonCol
from sqlalchemy import and_, or_, case
from flask import render_template, request, url_for, redirect, Blueprint
from flask_login import login_required, current_user
from app.views import admin_permission
from app.models import *
from app.competence import s
from forms import *
import json

competence = Blueprint('competence', __name__, template_folder='templates')

class DeleteCol(Col):
    def __init__(self, name, attr=None, attr_list=None, **kwargs):
        super(DeleteCol, self).__init__(
            name,
            attr=attr,
            attr_list=attr_list,
            **kwargs)

    def td_contents(self, item, attr_list):
        print item
        return '<a href="#" class="remove btn btn-sm btn-danger" id="'+str(item.id)+'"><span class="glyphicon glyphicon-remove"></span></a>'

class ItemTableSubsections(Table):
    name = Col('Area of Competence')
    type = Col('Evidence Type')
    comments = Col('Comments')
    id = DeleteCol('Remove')

class ItemTableDocuments(Table):
    qpulseno = Col('QPulse ID')
    title = Col('QPulse Document Title')

@competence.route('/list', methods=['GET', 'POST'])
def list_comptencies():

    data = s.query(Competence).all()
    return render_template('competences_list.html',data=data)

@competence.route('/add', methods=['GET', 'POST'])
def add_competence():
    form = AddCompetence()
    if request.method == 'POST':
        title = request.form['title']
        scope = request.form['scope']
        val_period = request.form['validity_period']
        comp_category=request.form['competency_type']
        c = Competence(title, scope, current_user.database_id, val_period, comp_category)
        s.add(c)
        s.commit()
        c_id = c.id
        doclist = request.form['doc_list'].split(',')
        for doc in doclist:
            add_doc = Documents(c_id=c_id, qpulse_no=doc)
            s.add(add_doc)
        s.commit()
        add_section_form = AddSection()

        constants = s.query(Section).filter(Section.constant == 1).all()
        result = {}
        for section in constants:
            if section.name not in result:
                result[section.name]={}
                result[section.name][str(section.id)]=[]
            subsections = s.query(ConstantSubsections).filter_by(s_id=section.id).all()
            result[section.name][str(section.id)].append(subsections)

       # print request.form(dir())
        return render_template('competence_section.html', form=add_section_form, c_id=c_id, result=result)

    return render_template('competence_add.html', form=form)

@competence.route('/addsections', methods=['GET', 'POST'])
def add_sections():
    print "hello"

    f = request.form
    c_id = request.args.get('c_id')
    print f
    for key in f.keys():
        if "subsections" in key:
            for value in f.getlist(key):
                print key, ":", value
                #c_id=request.args.get('c_id')
                s_id = key[0]
                item_add=s.query(ConstantSubsections.item).filter_by(id=value).all()
                evidence = s.query(EvidenceTypeRef.id).filter_by(type='Discussion').all()
                print s_id
                print item_add
                print evidence
                add_constant=Subsection(c_id=c_id, s_id=s_id, name=item_add, evidence=evidence, comments=None)
                s.add(add_constant)
                s.commit()


@competence.route('/section', methods=['GET', 'POST'])
def get_section():

    if request.method == 'POST':
        # add subsection section database
        pass
    text = request.json['text']

    c_id = request.json['c_id']
    val = request.json['val']
    form = SectionForm()
    subsection_form = AddSubsection()
    #method below gets the subsections for the section_id selected in the form
    result_count = s.query(Subsection).join(Competence).join(Section).join(EvidenceTypeRef).filter(
        and_(Competence.id == c_id, Section.id == val)).count()
    if result_count != 0:
        result = s.query(Subsection).join(Competence).join(Section).join(EvidenceTypeRef).filter(and_(Competence.id==c_id, Section.id==val)).values(Subsection.name, EvidenceTypeRef.type, Subsection.comments)

        table = ItemTableSubsections(result, classes=['table', 'table-striped', 'table-bordered' ,'section_'+str(val)])
    else:
        table = '<table class="section_'+str(val)+'"></table>'

    #print str(c_id) + ' ' + str(val) + ' ' + 'should get subsections for selected section'
    return jsonify(render_template('section.html',c_id=c_id, form=form, val=val, text=text, table=table, subsection_form=subsection_form))

@competence.route('/delete_subsection', methods=['GET', 'POST'])
def delete_subsection():
    print request.json
    c_id = request.json['c_id']
    s_id = request.json['s_id']
    s.query(Subsection).filter_by(c_id = request.json['c_id']).filter_by(id=request.json["id"]).delete()
    s.commit()
    result_count = s.query(Subsection).join(Competence).join(Section).join(EvidenceTypeRef).filter(
        and_(Competence.id == c_id, Section.id == s_id)).count()
    if result_count != 0:
        result = s.query(Subsection).join(Competence).join(Section).join(EvidenceTypeRef).filter(
            and_(Competence.id == c_id, Section.id == s_id)).values(Subsection.id, Subsection.name, EvidenceTypeRef.type,
                                                                   Subsection.comments)

        table = ItemTableSubsections(result, classes=['table', 'table-striped', 'table-bordered', 'section_' + str(s_id)])
    else:
        table = '<table class="section_' + str(s_id) + '"></table>'
    return jsonify(table)


@competence.route('/add_subsection_to_db', methods=['GET', 'POST'])
def add_sections_to_db():
    #method adds subsections to database
    name = request.json['name']
    evidence_id = request.json['evidence_id']
    comments = request.json['comments']
    c_id = request.json['c_id']
    s_id = request.json['s_id']
    sub = Subsection(name=name,evidence=int(evidence_id),comments=comments,c_id=c_id,s_id=s_id)
    print s.add(sub)
    print s.commit()
    result = s.query(Subsection).join(Competence).join(Section).join(EvidenceTypeRef).filter(Competence.id == c_id).filter(Section.id == s_id). \
        values(Subsection.id, Subsection.name, EvidenceTypeRef.type, Subsection.comments)

    table = ItemTableSubsections(result, classes=['table', 'table-bordered', 'table-striped', 'section_'+str(s_id)])
    #print str(c_id) + ' ' + str(s_id) + ' ' + 'should add new subsection to selected section'
    return jsonify(table)

# @competence.route('/get_constants',methods=['GET', 'POST'])
# def get_constant_sections():
#     #Method to get all subsections that have a constant flag in the database
#     constants = s.query(Subsection).filter(Section.constant == 1).values(Section.id, Section.name)
#     for constant in constants:
#         s_id=constant.id
#         name=constant.name
#         print s_id, name
#
#         return jsonify(render_template('section.html', c_id=c_id, form=form, val=val, text=text, table=table,
#                                        subsection_form=subsection_form))

@competence.route('/autocomplete_docs',methods=['GET'])
def document_autocomplete():
 doc_id = request.args.get('add_document')

 docs = s.query(Documents.qpulse_no).all()
 doc_list = []
 for i in docs:
     doc_list.append(i.qpulse_no)

 return jsonify(json_list=doc_list)

@competence.route('/get_docs',methods=['GET'])
def get_documents(c_id):
     c_id=1
     docid = request.json['add_document']
     documents=s.query(Documents).join(Competence).filter(competence.id == c_id)
     table =  ItemTableDocuments(documents, classes=['table', 'table-striped', docid])
     return jsonify(table)

@competence.route('/add_constant',methods=['GET','POST'])
def add_constant_subsection():
    s_id=request.json['s_id']
    print s_id
    item=request.json['item']
    print item
    add_constant=ConstantSubsections(s_id=s_id, item=item)
    s.add(add_constant)
    s.commit()
    return jsonify(add_constant.id)



