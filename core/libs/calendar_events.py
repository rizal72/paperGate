import time
import logging
import threading
from datetime import date, datetime, timedelta
from functools import wraps

import caldav
import httplib2.error
import humanize
import pytz
import requests.exceptions
import urllib3.exceptions
from icalevents.icalevents import events
from requests.exceptions import SSLError

import settings
from settings import TIMEZONE


# Retry configuration
MAX_RETRY_ATTEMPTS = 5
INITIAL_RETRY_DELAY = 1  # seconds
MAX_RETRY_DELAY = 60  # seconds


def retry_with_backoff(max_attempts=MAX_RETRY_ATTEMPTS, initial_delay=INITIAL_RETRY_DELAY, max_delay=MAX_RETRY_DELAY):
    """
    Decorator for retrying functions with exponential backoff.
    Retries on network-related exceptions only.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            delay = initial_delay

            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except (
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.SSLError,
                    urllib3.exceptions.NewConnectionError,
                    urllib3.exceptions.TimeoutError,
                    urllib3.exceptions.ProtocolError,
                    httplib2.error.ServerNotFoundError,
                    httplib2.error.HttpLib2Error,
                    OSError,  # Socket errors
                    TimeoutError,
                ) as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(f"{func.__name__} failed after {max_attempts} attempts: {e}")
                        raise

                    logger.warning(f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                                 f"Retrying in {delay}s...")
                    time.sleep(delay)

                    # Exponential backoff with jitter
                    delay = min(delay * 2, max_delay)

            return None
        return wrapper
    return decorator


CALENDAR_URLS = settings.CALENDAR_URLS
CALENDAR_REFRESH = settings.CALENDAR_REFRESH

timezone = pytz.timezone(TIMEZONE)
logger = logging.getLogger('pitftmanager.libs.calendar')


def sort_by_date(obj: dict):
    """
    Sort the events or tasks by date
    :param obj: dict containing summary and start/due date
    :return: the same object, with time added if needed
    """
    if obj.get("start"):
        if isinstance(obj["start"], date) and not isinstance(obj["start"], datetime):
            return datetime.combine(obj["start"], datetime.min.time(), timezone)
        if not obj["start"].tzinfo:
            return timezone.localize(obj["start"])
        return obj["start"]
    elif obj.get("due"):
        if not obj["due"]:
            return datetime.fromisocalendar(4000, 1, 1)
        if isinstance(obj["due"], date) and not isinstance(obj["due"], datetime):
            return datetime.combine(obj["due"], datetime.min.time(), timezone)
        if not obj["due"].tzinfo:
            return timezone.localize(obj["due"])
        return obj["due"]
    else:
        return timezone.localize(datetime.max)


class Calendar(threading.Thread):
    """
    This class handles the calendar events and tasks
    """
    timezone = None
    refresh_interval: int = CALENDAR_REFRESH
    events: list = []
    tasks: list = []
    thread_lock: threading.Lock = threading.Lock()

    def __init__(self):
        """
        Initialize the timezone
        """
        super().__init__()
        self.timezone = pytz.timezone(TIMEZONE)
        self.name = "Calendar"
        self.shutdown = threading.Event()

    def run(self):
        thread_process = threading.Thread(target=self.calendar_loop)
        # run thread as a daemon so it gets cleaned up on exit.
        thread_process.daemon = True
        thread_process.start()
        self.shutdown.wait()

    def calendar_loop(self):
        while not self.shutdown.is_set():
            self.refresh_interval -= 1
            time.sleep(1)
            if self.refresh_interval < 1:
                self.get_latest_events()
                self.refresh_interval = CALENDAR_REFRESH

    def stop(self):
        self.shutdown.set()

    def standardize_date(self, arg):
        """
        Adds time to dates to make datetimes as needed
        :param arg: an object containing a summary and date
        :return: a new datetime object, or the same object if no changes were needed
        """
        if isinstance(arg, datetime) and not arg.tzinfo:
            logger.debug("Object has no timezone")
            return self.timezone.localize(arg)
        elif isinstance(arg, date) and not isinstance(arg, datetime):
            logger.debug("Object has no time")
            return datetime.combine(arg, datetime.min.time(), self.timezone)
        else:
            return arg

    @retry_with_backoff()
    def _fetch_webcal_events(self, url):
        """
        Fetch events from webcal URL with retry logic.
        :param url: the URL of the webcal
        :return: list of events
        """
        return events(url, start=datetime.today(),
                     end=datetime.today() + timedelta(days=14))

    def get_events_from_webcal(self, new_events, url):
        """
        Retrieve events from webcal and append them to the list
        :param new_events: list of new events
        :param url: the URL of the webcal
        """
        try:
            timeline = self._fetch_webcal_events(url)
            for event in timeline:
                start = event.start
                end = event.end if hasattr(event, 'end') else None
                summary = event.summary

                new_events.append({
                    'start': start,
                    'end': end,
                    'summary': summary
                })
        except Exception as error:
            # Already logged by retry decorator, just track failure
            logger.error(f'Failed to fetch webcal calendar "{url}" after all retries')
            pass

    @retry_with_backoff()
    def _get_caldav_principal(self, url, username, password):
        """
        Get CalDAV principal with retry logic.
        :param url: URL of CalDAV server
        :param username: CalDAV username
        :param password: CalDAV password
        :return: principal object
        """
        client = caldav.DAVClient(url=url, username=username, password=password)
        return client.principal()

    @retry_with_backoff()
    def _fetch_caldav_calendars(self, principal):
        """
        Fetch calendars from CalDAV principal with retry logic.
        :param principal: CalDAV principal object
        :return: list of calendars
        """
        return principal.calendars()

    @retry_with_backoff()
    def _fetch_caldav_events(self, calendar, start, end):
        """
        Fetch events from CalDAV calendar with retry logic.
        :param calendar: CalDAV calendar object
        :param start: start date
        :param end: end date
        :return: list of events
        """
        return calendar.date_search(start=start, end=end, expand=True)

    @retry_with_backoff()
    def _fetch_caldav_todos(self, calendar):
        """
        Fetch todos from CalDAV calendar with retry logic.
        :param calendar: CalDAV calendar object
        :return: list of todos
        """
        return calendar.todos()

    def get_events_from_caldav(self, new_events, new_tasks, url, username, password):
        """
        Retrieve events and tasks from CalDAV
        :param new_events: list of new events
        :param new_tasks: list of new tasks
        :param url: URL of CalDAV server
        :param username: CalDAV user name
        :param password: CalDAV password
        :return: the list of events
        """
        try:
            principal = self._get_caldav_principal(url, username, password)
        except (caldav.lib.error.AuthorizationError, Exception) as error:
            logger.error(f"Failed to connect to CalDAV server '{url}' after all retries: {error}")
            return

        try:
            calendars = self._fetch_caldav_calendars(principal)
        except Exception as error:
            logger.error(f"Failed to fetch calendars from '{url}' after all retries: {error}")
            return

        for cal in calendars:
            try:
                calendar_events = self._fetch_caldav_events(
                    cal,
                    start=datetime.today(),
                    end=datetime.today() + timedelta(days=7)
                )
                for event in calendar_events:
                    start = self.standardize_date(event.vobject_instance.vevent.dtstart.value)
                    summary = event.vobject_instance.vevent.summary.value

                    # Get end time if available
                    try:
                        end = self.standardize_date(event.vobject_instance.vevent.dtend.value)
                    except AttributeError:
                        end = None

                    new_events.append({
                        'start': start,
                        'end': end,
                        'summary': summary
                    })

                todos = self._fetch_caldav_todos(cal)

                for todo in todos:
                    try:
                        due = self.standardize_date(todo.vobject_instance.vtodo.due.value)
                    except AttributeError:
                        due = None

                    summary = todo.vobject_instance.vtodo.summary.value

                    new_tasks.append({
                        'due': due,
                        'summary': summary
                    })
            except Exception as error:
                logger.warning(f"Failed to process calendar in '{url}': {error}")
                continue

    def get_latest_events(self):
        """
        Update events and tasks
        """
        logger.debug("Started reading calendars...")
        self.thread_lock.acquire()
        new_events = []
        new_tasks = []

        for connection in CALENDAR_URLS:
            if str(connection["type"]).lower() == 'webcal':
                try:
                    self.get_events_from_webcal(new_events, connection["url"])
                except KeyError as error:
                    logger.error("No URL specified for calendar")
                    logger.error(error)
            elif str(connection['type']).lower() == 'caldav':
                try:
                    self.get_events_from_caldav(new_events, new_tasks, connection["url"],
                                                connection["username"], connection["password"])
                except KeyError as error:
                    if connection.get('url'):
                        logger.error("Error reading calendar: {}".format(connection['url']))
                    else:
                        logger.error("No URL specified for calendar")
                    logger.error(error)
            else:
                logger.error("calendar type not recognized: {0}".format(str(connection["type"])))

        # Filter out past events - keep only today and future
        new_events = [e for e in new_events if e["start"].date() >= date.today()]

        new_events.sort(key=sort_by_date)
        new_tasks.sort(key=sort_by_date)

        logger.debug("done!")

        self.events = new_events
        self.tasks = new_tasks

        self.thread_lock.release()

    def events_as_string(self):
        """
        Get the current events as a string
        :return: list of events
        """
        text = ''

        for obj in self.events:
            text += self.humanized_datetime(obj["start"]) + '\n'
            text += obj["summary"].replace('\n', ' ') + '\n'

        return text

    def tasks_as_string(self):
        """
        Get the current tasks as a string
        :return: list of tasks
        """
        text = ''

        for obj in self.tasks:
            text += "* " + obj["summary"].replace('\n', ' ') + '\n'
            if obj["due"]:
                text += "  - Due: " + self.humanized_datetime(obj["due"]) + "\n"

        return text

    def humanized_datetime(self, dt: datetime):
        """
        Get a human-readable interpretation of a datetime
        :param dt: datetime to humanize
        :return: str
        """
        try:
            obj = self.timezone.localize(dt)
        except ValueError:
            obj = dt
        except AttributeError:
            obj = dt
        if (isinstance(obj, date) and not isinstance(obj, datetime)) or obj.date() > datetime.today().date():
            return humanize.naturaldate(obj)
        else:
            return humanize.naturaltime(obj, when=datetime.now(self.timezone))


calendar = Calendar()


def get_calendar():
    """
    Retrieve main Calendar object
    :return: Calendar
    """
    return calendar


def update_calendar():
    """
    Update calendar events and tasks
    :return: None
    """
    calendar.refresh_interval = 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    calendar.get_latest_events()
    for event in calendar.events:
        logger.info(event.start)
        logger.info(event.summary)
