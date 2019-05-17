#! /usr/bin/env python

from datetime import timedelta
from garminexport.garminclient import GarminClient
import garminexport.backup
from garminexport.backup import export_formats
from garminexport.retryer import (
    Retryer, ExponentialBackoffDelayStrategy, MaxRetriesStopStrategy)
import logging
import os
import re
import sys
import traceback
import json

logging.basicConfig(
    level=logging.INFO, format="%(asctime)-15s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR
}

DEFAULT_MAX_RETRIES = 7

if __name__ == "__main__":
    with open ('/data/setup.json') as json_file:
        data = json.load (json_file)
        username = data ['username']
        password = data ['password']
        backup_dir = '/data/activity'
        if data ['log_level'] is None:
            log_level = 'INFO'
        else:
            log_level = data ['log_level']
        formats = data ['formats']
           
    if not log_level in LOG_LEVELS:
        raise ValueError("Illegal log-level: {}".format(log_level))

    # if no --format was specified, all formats are to be backed up
    formats = formats if formats else export_formats
    log.info("backing up formats: %s", ", ".join(formats))

    logging.root.setLevel(LOG_LEVELS[log_level])

    try:
        if not os.path.isdir(backup_dir):
            os.makedirs(backup_dir)

        if not password:
            raise ValueError ("Password must be provided")

        # set up a retryer that will handle retries of failed activity
        # downloads
        retryer = Retryer(
            delay_strategy=ExponentialBackoffDelayStrategy(
                initial_delay=timedelta(seconds=1)),
            stop_strategy=MaxRetriesStopStrategy(DEFAULT_MAX_RETRIES))

        with GarminClient(username, password) as client:
            # get all activity ids and timestamps from Garmin account
            log.info("scanning activities for %s ...", username)
            activities = set(retryer.call(client.list_activities))
            log.info("account has a total of %d activities", len(activities))

            missing_activities = garminexport.backup.need_backup(
                activities, backup_dir, formats)
            backed_up = activities - missing_activities
            log.info("%s contains %d backed up activities", backup_dir, len(backed_up))

            log.info("activities that aren't backed up: %d",
                     len(missing_activities))

            for index, activity in enumerate(missing_activities):
                id, start = activity
                log.info("backing up activity %d from %s (%d out of %d) ..." % (id, start, index+1, len(missing_activities)))
                try:
                    garminexport.backup.download(
                        client, activity, retryer, backup_dir, formats)
                except Exception as e:
                    log.error(u"failed with exception: %s", e)
                    raise
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        log.error(u"failed with exception: %s", str(e))
