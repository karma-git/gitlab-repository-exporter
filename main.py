import logging
import os
import time
import re
from datetime import datetime

import schedule

import gitlab
from gitlab.v4.objects import Project, ProjectMergeRequest
from gitlab.v4.objects.branches import ProjectBranch

from prometheus_client import start_http_server, Gauge

# app settings
APP_WAIT_PERIOD = int(os.environ.get("APP_WAIT_PERIOD", 1))
APP_COLLECT_PERIOD = int(os.environ.get("APP_COLLECT_PERIOD", 60))
APP_BIND_PORT = int(os.environ.get("APP_BIND_PORT", 8000))
APP_DEBUG = not bool(os.environ.get("APP_DEBUG", "").lower() in ("", "0", "no", "false"))

# exporter settings
APP_GITLAB_URL = os.environ.get("APP_GITLAB_URL", "https://gitlab.com/")
APP_GITLAB_ACCESS_TOKEN = os.environ["APP_GITLAB_ACCESS_TOKEN"]
APP_GITLAB_PROJECT_ID = os.environ["APP_GITLAB_PROJECT_ID"]

logging.basicConfig(
    level=logging.DEBUG if APP_DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)


def unix_timestamp(date: str) -> float:
    try:
        # catching format 2021-12-10T12:44:00.000+00:00
        result = datetime.timestamp(datetime.fromisoformat(date)) * 1000
    except ValueError:
        # else we should take 2022-04-04T16:18:08.132Z
        regex = r'^[\d]{4}-[\d]{2}-[\d]{2}T[\d]{2}:[\d]{2}:[\d]{2}'
        match = re.match(regex, date, re.DOTALL)
        if match:
            dt: datetime = datetime.strptime(match.group(), '%Y-%m-%dT%H:%M:%S')
            result = datetime.timestamp(dt) * 1000
    finally:
        return result


def _init_metrics() -> tuple:
    branch_count = Gauge(
        name="branch_count",
        documentation="number of branch in the project",
        labelnames=["project_url"],
    )

    branch_ttl = Gauge(
        name="branch_ttl",
        documentation="detail info for branches in the project",
        labelnames=["project_url", "branch_name", "committer"],
    )

    mr_count = Gauge(
        name="mr_count",
        documentation="number of mrs in the project",
        labelnames=["project_url"],
    )

    mr_ttl = Gauge(
        name="mr_ttl",
        documentation="detail info for mrs in the project",
        labelnames=["project_url",
                    "title",
                    "branch_name",
                    "author",
                    'votes_diff'
                    ],
    )

    return branch_count, branch_ttl, mr_count, mr_ttl


def gitlab_branches(project: Project) -> tuple:
    branches_batch = []
    branches = project.branches.list(all=True)
    branches_count = len(branches)
    branch: ProjectBranch
    for branch in branches:
        data = {'project_url': project.http_url_to_repo,
                'branch_name': branch.name,
                'committer': branch.commit["committer_email"],
                "commit_date": unix_timestamp(branch.commit["committed_date"])
                }
        # logging.debug(f"Branch data: {data}")
        branches_batch.append(data)
    return branches_count, branches_batch


def gitlab_merge_requests(project: Project) -> tuple:
    mrs_batch = []
    mrs = project.mergerequests.list(state='opened', all=True)
    mrs_count = len(mrs)
    mr: ProjectMergeRequest
    for mr in mrs:
        data = {
            'project_url': mr.web_url,
            'title': mr.title,
            'branch_name': mr.source_branch,
            'author': mr.author["username"],
            'updated_at': unix_timestamp(mr.updated_at),
            'votes_diff': mr.upvotes - mr.downvotes,
        }
        # logging.debug(f"MR data: {data}")
        mrs_batch.append(data)
    return mrs_count, mrs_batch


def collect() -> None:
    # Temporary list used to update values in atomic-like approach
    labels_list = []

    logging.info("Collecting branch data")

    count, data = gitlab_branches(project)
    logging.info(f"branches-count: {count}")

    branch_count.labels(project_url=project_url).set(count)

    for branch in data:
        logging.debug(f"Processing branch: {branch['branch_name']}")
        timestamp = branch.pop("commit_date")
        labels_list.append((branch, timestamp))

    branch_ttl.clear()

    for labels, value in labels_list:
        branch_ttl.labels(**labels).set(value)

    labels_list.clear()

    logging.info("Collecting MR data")

    count, data = gitlab_merge_requests(project)
    logging.info(f"mrs-count: {count}")

    mr_count.labels(project_url=project_url).set(count)

    for mr in data:
        logging.debug(f"Processing mr: {mr['project_url']}")
        timestamp = mr.pop("updated_at")
        labels_list.append((mr, timestamp))

    mr_ttl.clear()

    for labels, value in labels_list:
        mr_ttl.labels(**labels).set(value)


if __name__ == "__main__":
    # GitLab API init
    gl = gitlab.Gitlab(url=APP_GITLAB_URL, private_token=APP_GITLAB_ACCESS_TOKEN)
    project = gl.projects.get(APP_GITLAB_PROJECT_ID)
    project_url = project.http_url_to_repo

    # metrics init
    branch_count, branch_ttl, \
    mr_count, mr_ttl \
        = _init_metrics()

    logging.debug("Debug mode enabled")

    logging.info("Running daemon")

    logging.info("Starting HTTP server")
    start_http_server(APP_BIND_PORT)

    logging.info(f"Starting schedule for project {project_url}")
    schedule.every(APP_COLLECT_PERIOD).seconds.do(collect)  # TODO: metrics and project instance as params

    while True:
        schedule.run_pending()
        time.sleep(APP_WAIT_PERIOD)

# TODO: shadow functions params
