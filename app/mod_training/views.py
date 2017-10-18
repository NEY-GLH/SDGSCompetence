from flask import Flask, render_template, redirect, request, url_for, session, current_app, Blueprint
from flask_login import login_required, login_user, logout_user, LoginManager, UserMixin, \
    current_user
from competence import app, s
from app.models import *
from sqlalchemy.sql.expression import func, and_, or_, case, exists

training = Blueprint('training', __name__, template_folder='templates')

###########
# Queries #
###########
def get_competence_by_user(c_id, u_id):
    """
    Method to get information for competence for a given user

    :param c_id: ID for competence
    :param u_id: ID of user
    :return:
    """
    #get ID for user
    try:
        id = int(u_id)
    except TypeError:
        user_result = s.query(Users).filter(Users.login == u_id).values(Users.id)
        id = 0
        for u in user_result:
            id = u[0]
            break

    #get info for competence (assessments table)
    competence_result = s.query(Assessments).outerjoin(Users, Assessments.signoff_id==Users.id).outerjoin(Subsection).outerjoin(Section)\
        .outerjoin(Competence, Subsection.c_id == Competence.id).\
        outerjoin(AssessmentStatusRef, Assessments.status==AssessmentStatusRef.id).\
        outerjoin(EvidenceTypeRef).\
        filter(and_(Assessments.user_id == id, Competence.id == c_id)).\
        values(Section.name, Subsection.name.label('area_of_competence'), Subsection.comments.label('notes'), EvidenceTypeRef.type,
               AssessmentStatusRef.status, (Users.first_name + ' ' + Users.last_name).label('assessor'),
               Assessments.date_completed, Assessments.date_expiry, Assessments.comments.label('training_comments'))
    result = {}
    for c in competence_result:
        if c.name not in result.keys():
            result[c.name] = {'complete':0, 'total':0, 'subsections':[]}
        subsection = {'name':c.area_of_competence,
                      'status':c.status,
                      'evidence_type':c.type,
                      'assessor':filter_for_none(c.assessor),
                      'date_of_completion':filter_for_none(c.date_completed),
                      'notes':filter_for_none(c.notes),
                      'training_comments':filter_for_none(c.training_comments),
                      'trainer':filter_for_none('c.trainer'),
                      'date_of_training':filter_for_none('training_date')}
        if c.date_completed:
            result[c.name]['complete'] += 1
        result[c.name]['total'] += 1
        result[c.name]['subsections'].append(subsection)
    return result

def get_competence_summary_by_user(c_id, u_id):
    """

    :param c_id:
    :param u_id:
    :return:
    """
    try:
        id = int(u_id)
    except TypeError:
        user_result = s.query(Users).filter(Users.login == u_id).values(Users.id)
        id = 0
        for u in user_result:
            id = u[0]
            break

    competence_result = s.query(Assessments).outerjoin(Users, Users.id == Assessments.user_id).outerjoin(Subsection).outerjoin(Section). \
        outerjoin(Competence, Subsection.c_id == Competence.id).outerjoin(AssessmentStatusRef,
                                                                 Assessments.status == AssessmentStatusRef.id).\
        outerjoin(ValidityRef, Competence.validity_period==ValidityRef.id).\
        filter(and_(Users.id == id, Competence.id == c_id)). \
        values((Users.first_name + ' ' +  Users.last_name).label('user'),
               Competence.title,
               Competence.qpulsenum,
               Competence.scope,
               ValidityRef.months,
               func.max(Assessments.date_assigned).label('assigned'),
               func.max(Assessments.date_activated).label('activated'),
               case([
                   (s.query(Assessments).\
                       outerjoin(Subsection).\
                       outerjoin(Competence).\
                       filter(and_(Users.id == id, Competence.id == c_id, Assessments.date_completed == None)).exists(),
                    None)],
                   else_=func.max(Assessments.date_completed)).label('completed'),
               case([
                   (s.query(Assessments).\
                       outerjoin(Subsection).\
                       outerjoin(Competence).\
                       filter(and_(Users.id == id, Competence.id == c_id, Assessments.date_expiry == None)).exists(),
                    None)],
                   else_=func.max(Assessments.date_expiry)).label('expiry'))
    for comp in competence_result:
        return comp

def activate_assessments(c_id, u_id):
    """


    :return:
    """
    for r in s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Active").values(AssessmentStatusRef.id):
        activated = r.id
    for r in s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Assigned").values(AssessmentStatusRef.id):
        assigned = r.id
    print(assigned)

    statement = s.query(Assessments).\
        filter(and_(Assessments.user_id == u_id, Assessments.status == activated, Subsection.c_id == c_id)).\
        update({Assessments.status: assigned, Assessments.date_activated: datetime.date.today()})

###########
# Methods #
###########
def filter_for_none(value):
    """
    Method to check if value returned from database is none and replace with '-'

    :param value: the value returned from the database
    :return: if the value is none, the method return '-', else the value from the database is returned
    """
    if not value:
        return '-'
    else:
        return value

###########
#  Views  #
###########

@training.route('/view', methods=['GET', 'POST'])
def view_current_competence():
    """


    :return:
    """
    if request.method == 'GET':
        print('here')
        c_id = request.args.get('c_id')
        user = request.args.get('user')
        if not user:
            user = current_user.id

        competence_summary = get_competence_summary_by_user(1, user)
        section_list = get_competence_by_user(1, user)

        print(section_list)
        # return template populated
        return render_template('complete_training.html', user=competence_summary.user, number=competence_summary.qpulsenum,
                               title=competence_summary.title, validity=competence_summary.months,
                               scope=competence_summary.scope, section_list=section_list,
                               assigned=competence_summary.assigned, activated = filter_for_none(competence_summary.activated),
                               completed=filter_for_none(competence_summary.completed), expires=filter_for_none(competence_summary.expiry))

@training.route('/activate', methods=['GET', 'POST'])
def activate_competence():
    """
    Method to change all assessments for a current competence to activated.

    :return:
    """
    u_id = request.args.get('user')
    c_id = request.args.get('competence')

    activate_assessments(c_id, u_id)

    return url_for('view_current_competence', c_id=c_id, user=u_id)

