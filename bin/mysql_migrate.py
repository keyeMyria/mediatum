# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details

mediaTUM MySQL to PostgreSQL migration.

mysql_migration.py <action>

Use 'everything' or run a selection of actions. The actions must be run in the given sequence!

action is one of:

* pgloader: migrate data from mysql DB to postgres import schema (edit config in migration/mysql_migration.load first!)
* prepare: prepare functions for data migration from import schema
* core: basic migrations from import schema to mediatum schema
* users: migrate users and usergroups in mediatum schema
* dynusers: migrate users from dynauth plugin
* permissons: migrate node permissons from import schema to mediatum schema
* everything: run all tasks above

Database changes are commited after all actions have been run.

"""
from __future__ import print_function

import configargparse
import logging
import os.path
import subprocess
logging.getLogger().setLevel(logging.WARN)
from core.init import basic_init
from core.database.postgres.connector import read_and_prepare_sql
from collections import OrderedDict
from bin.manage import vacuum_analyze_tables

basic_init()
import core.database.postgres


core.database.postgres.SLOW_QUERY_SECONDS = 1000
logging.getLogger("migration.acl_migration").trace_level = logging.ERROR
logging.getLogger("core.database.postgres").trace_level = logging.ERROR

logg = logging.getLogger("mysql_migrate.py")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARN)

from core import db

s = db.session

MIGRATION_DIR = os.path.join(os.path.dirname(__file__), "../migration")

PGLOADER_BINARY = "pgloader"
DOCKER_PGLOADER_IMAGE = "dpausp/pgloader"


def pgloader(s=None):
    if args.docker:
        docker_call = ["docker", "run", "--rm", "-v", "{}:/tmp".format(os.path.abspath(MIGRATION_DIR))]
        links = []
        for link in args.link:
            links.append("--link")
            links.append(link)

        subprocess.call(docker_call + links + [DOCKER_PGLOADER_IMAGE, "pgloader", "/tmp/mysql_migration.load"])
    else:
        script_path = os.path.join(MIGRATION_DIR, "mysql_migration.load")
        subprocess.call([PGLOADER_BINARY, "--verbose", script_path])


def prepare_import_migration(s):
    for sql_file in ["migration.sql", "acl_migration.sql", "user_migration.sql"]:
        s.execute(read_and_prepare_sql(sql_file, MIGRATION_DIR))
    logg.info("finished db preparations")


def migrate_core(s):
    s.execute("SELECT mediatum.migrate_core()")
    logg.info("finished node + attrs, nodefile and nodemapping migration")


def users(s):
    s.execute("SELECT mediatum.migrate_usergroups()")
    s.execute("SELECT mediatum.migrate_internal_users()")
    logg.info("finished user migration")


def dynusers(s):
    s.execute("SELECT mediatum.migrate_dynauth_users()")
    logg.info("finished dynauth user migration")


def permissions(s):
    from migration import acl_migration
    acl_migration.migrate_access_entries()
    acl_migration.migrate_rules()
    logg.info("finished permissions migration")


def inherited_permissions(s):
    s.commit()
    vacuum_analyze_tables(s)
    try:
        s.execute("SELECT mediatum.create_all_inherited_access_rules_read()")
        s.execute("SELECT mediatum.create_all_inherited_access_rules_write()")
        s.execute("SELECT mediatum.create_all_inherited_access_rules_data()")
    except:
        s.execute("TRUNCATE mediatum.access_rule, mediatum.access_ruleset CASCADE")
        s.commit()
        raise

    logg.info("created inherited access rules")


def everything(s):
    pgloader()
    prepare_import_migration(s)
    migrate_core(s)
    users(s)
    dynusers()
    permissions(s)
    inherited_permissions(s)


actions = OrderedDict([
    ("pgloader", pgloader),
    ("prepare", prepare_import_migration),
    ("core", migrate_core),
    ("users", users),
    ("dynusers", dynusers),
    ("permissions", permissions),
    ("inherited_permissions", inherited_permissions),
    ("everything", everything)
])

if __name__ == "__main__":
    parser = configargparse.ArgumentParser("mediaTUM mysql_migrate.py")
    parser.add_argument("--full-transaction", default=False, action="store_true")
    parser.add_argument("--docker", default=False, action="store_true", help="use the prebuilt docker image for pgloader")
    parser.add_argument("--link", default=[], action="append", help="docker link to another container like: --link=postgres:postgres")
    parser.add_argument("action", nargs="*", choices=actions.keys())

    print()
    print("-" * 80)
    print()

    args = parser.parse_args()

    for action in args.action:
        actions[action](s)
        if not args.full_transaction:
            logg.info("commit after action %s", action)
            s.commit()

    s.commit()