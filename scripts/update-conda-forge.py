#!/usr/bin/env python

import logging
import os
from operator import itemgetter
from pathlib import Path

import github
import jinja2
import requests

logging.basicConfig(format="[%(asctime)s] %(message)s", level=logging.INFO)

CONDA_FORGE_INDEX = Path("status") / "conda-forge" / "index.html"
CONDA_FORGE_STATUS_TEMPLATE = jinja2.Template("""
---
---
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <meta name="description" content="">
    <meta name="author" content="">
    <link rel="icon" href="../../../../favicon.ico">
    <title>Conda status</title>
    <!-- Bootstrap core CSS -->
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous">
  </head>
  <body class="bg-light">
    <div class="container">
      <h1>Conda-forge feedstock status</h1>
      <table class="table table-sm table-hover table-striped table-condensed">
        <caption>Status of conda-forge builds for which <a href="https://github.com/duncanmmacleod" target="_blank">@duncanmmacleod</a> is a maintainer</caption>
        <thead>
          <tr><th>Package</th><th>Build</th><th>Issues</th><th>Pull requests</th></tr>
        </thead>
        <tbody>{% for feedstock in feedstocks %}
          {{ '{%' }} include cf.html name="{{ feedstock['name'] }}" azureid="{{ feedstock['azureid'] }}" {{ '%}' }}
{%- endfor %}
        </tbody>
      </table>
    </div>
  </body>
</html>
""".strip())

SKIP = {
    "all-members",
}


def get_azure_build_id(session, feedstock_name):
    url = (
        "https://dev.azure.com/conda-forge/feedstock-builds/_apis/build/"
        "definitions?name={}-feedstock".format(feedstock_name)
    )
    resp = session.get(url)
    resp.raise_for_status()
    try:
        return resp.json()['value'][0]['id']
    except IndexError:
        print("Failed to query for {}".format(feedstock_name))
        raise


def is_archived(gh, feedstock_name):
    return gh.get_repo(
        "conda-forge/{}-feedstock".format(feedstock_name),
    ).archived


gh = github.Github(os.environ["GITHUB_PAT_READ_USER"])
feedstocks = []
with requests.Session() as sess:
    for team in gh.get_user().get_teams():
        name = team.name
        if (
            name in SKIP
            or team.organization.name != "conda-forge"
            or is_archived(gh, name)
        ):
            continue
        azureid = get_azure_build_id(sess, name)
        feedstocks.append({"name": name, "azureid": azureid})
        logging.info("found {} ({})".format(name, azureid))
feedstocks.sort(key=itemgetter('name'))

with open(CONDA_FORGE_INDEX, "w") as f:
    print(CONDA_FORGE_STATUS_TEMPLATE.render(feedstocks=feedstocks), file=f)
logging.info("updated {}".format(CONDA_FORGE_INDEX))
