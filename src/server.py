#!/usr/bin/env python
import sys
from datetime import datetime

from tinydb import TinyDB, Query, where
from jira import JIRA, resources

from django import forms
from django.conf import settings
from django.conf.urls.static import static
from django.core import wsgi, management, cache
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import path, reverse_lazy
from django.shortcuts import render


db = TinyDB("db.json")
credentials_tbl = db.table("credentials")


if not settings.configured:
    settings.configure(
        DEBUG=True,
        MIDDLEWARE=["server.credentials_middleware"],
        INSTALLED_APPS=["django.contrib.staticfiles"],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": ["src/templates"],
            }
        ],
        STATIC_URL="/static/",
        STATICFILES_DIRS=["src/static"],
        STATICFILES_FINDERS=["django.contrib.staticfiles.finders.FileSystemFinder"],
        ROOT_URLCONF="server",
        SECRET_KEY="selfiesecret",
    )


def credentials_middleware(get_response):
    def middleware(request: HttpRequest):
        table = db.table("credentials")
        if not table.all() and not request.path.endswith("login"):
            return HttpResponseRedirect(reverse_lazy("login"))
        return get_response(request)

    return middleware


class LoginForm(forms.Form):
    jira_instance = forms.URLField()
    jira_email = forms.EmailField()
    jira_token = forms.CharField()


def login_view(request: HttpRequest):
    table = db.table("credentials")
    form = LoginForm()
    if request.POST:
        form = LoginForm(request.POST)
        if form.is_valid():
            table.insert(form.cleaned_data)
            return HttpResponseRedirect(reverse_lazy("timer"))
    return render(request, "login.html", {"form": form})


def stopwatch(request: HttpRequest):
    table = db.table("records")
    last_record = None
    active_project = None
    active_task = None
    running_timer = None
    elapsed_time = None
    record_q = Query()
    # Searching only in unfinished records
    records = table.search(~record_q.end.exists())
    if records:
        last_record = records[0]
        active_project = records[0]["project"]
        active_task = records[0]["task"]
        running_timer = records[0]["timer"]
    if request.method == "POST":
        if last_record:
            table.update(
                {"end": datetime.now().strftime("%Y-%M-%d %H:%m:%S")},
                doc_ids=[last_record.doc_id],
            )
        if "close" in request.POST:
            active_project = None
            active_task = None
            running_timer = None
        else:
            active_project = request.POST["project"]
            active_task = db.table("project_settings").get(
                where("project") == active_project
            )["task"]
            running_timer = {"start": datetime.now().strftime("%Y-%M-%d %H:%m:%S")}
            table.insert(
                {"project": active_project, "task": active_task, "timer": running_timer}
            )
    if running_timer:
        elapsed_time = str(
            datetime.now()
            - datetime.strptime(running_timer["start"], "%Y-%M-%d %H:%m:%S")
        ).split(".")[0]
    return render(
        request,
        "timer.html",
        {
            "tabs": ["log", "report", "settings"],
            "selected_tab": "log",
            "projects": db.table("project_settings").all(),
            "active_project": active_project,
            "active_task": active_task,
            "running_timer": running_timer,
            "elapsed_time": elapsed_time,
        },
    )


def report_view(request: HttpRequest):
    table = db.table("records")
    records = table.all()
    return render(
        request,
        "report.html",
        {
            "tabs": ["log", "report", "settings"],
            "selected_tab": "report",
            "rows": records,
        },
    )


def get_jira_client():
    credentials = credentials_tbl.all()[0]
    return JIRA(
        credentials["jira_instance"],
        basic_auth=(credentials["jira_email"], credentials["jira_token"]),
        options={"agile_rest_path": resources.GreenHopperResource.AGILE_BASE_REST_PATH},
    )


class ProjectForm(forms.Form):
    project = forms.CharField()
    task = forms.CharField()


def settings_view(request: HttpRequest):
    projects = cache.cache.get("projects")
    tasks = cache.cache.get("timetracking_tasks")
    if projects is None:
        client = get_jira_client()
        projects = {p.key: p.name for p in client.projects()}
        tasks = {
            i.key: {"summary": i.fields.summary}
            for i in client.search_issues(
                "issuetype = Time-Tracking", fields="summary", maxResults=False
            )
        }
        cache.cache.set("projects", projects)
        cache.cache.set("timetracking_tasks", tasks)
    ProjectFormFormSet = forms.formset_factory(ProjectForm, extra=8, max_num=8)
    formset = ProjectFormFormSet(initial=db.table("project_settings").all())
    if request.method == "POST":
        formset = ProjectFormFormSet(
            request.POST, initial=db.table("project_settings").all()
        )
        if formset.is_valid():
            db.drop_table("project_settings")
            db.table("project_settings").insert_multiple(
                [fdata for fdata in formset.cleaned_data if fdata]
            )
    return render(
        request,
        "settings.html",
        {
            "tabs": ["log", "report", "settings"],
            "selected_tab": "settings",
            "projects": projects,
            "tasks": tasks,
            "formset": formset,
        },
    )


urlpatterns = [
    path("", stopwatch, name="log"),
    path("login", login_view, name="login"),
    path("settings", settings_view, name="settings"),
    path("report", report_view, name="report"),
] + static(settings.STATIC_URL)

app = wsgi.get_wsgi_application()

if __name__ == "__main__":
    management.execute_from_command_line(sys.argv)
