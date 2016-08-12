# -*- coding: utf-8 -*-
#
""" Drag and Drop v2 XBlock """
# Imports ###########################################################

import copy
import json
import urllib
import webob

from xblock.core import XBlock
from xblock.exceptions import JsonHandlerError
from xblock.fields import Scope, String, Dict, Float, Boolean, Integer
from xblock.fragment import Fragment
from xblockutils.resources import ResourceLoader
from xblockutils.settings import XBlockWithSettingsMixin, ThemableXBlockMixin

from .utils import _, FeedbackMessages, DummyTranslationService
from .default_data import DEFAULT_DATA


# Globals ###########################################################

loader = ResourceLoader(__name__)


# Classes ###########################################################

@XBlock.wants('settings')
@XBlock.needs('i18n')
class DragAndDropBlock(XBlock, XBlockWithSettingsMixin, ThemableXBlockMixin):
    """
    XBlock that implements a friendly Drag-and-Drop problem
    """
    STANDARD_MODE = "standard"
    ASSESSMENT_MODE = "assessment"

    display_name = String(
        display_name=_("Title"),
        help=_("The title of the drag and drop problem. The title is displayed to learners."),
        scope=Scope.settings,
        default=_("Drag and Drop"),
    )

    mode = String(
        display_name=_("Mode"),
        help=_(
            "Standard mode: the problem provides immediate feedback each time "
            "a learner drops an item on a target zone. "
            "Assessment mode: the problem provides feedback only after "
            "a learner drops all available items on target zones."
        ),
        scope=Scope.settings,
        values=[
            {"display_name": _("Standard"), "value": STANDARD_MODE},
            {"display_name": _("Assessment"), "value": ASSESSMENT_MODE},
        ],
        default=STANDARD_MODE
    )

    max_attempts = Integer(
        display_name=_("Maximum attempts"),
        help=_(
            "Defines the number of times a student can try to answer this problem. "
            "If the value is not set, infinite attempts are allowed."
        ),
        scope=Scope.settings,
        default=None,
    )

    show_title = Boolean(
        display_name=_("Show title"),
        help=_("Display the title to the learner?"),
        scope=Scope.settings,
        default=True,
    )

    question_text = String(
        display_name=_("Problem text"),
        help=_("The description of the problem or instructions shown to the learner"),
        scope=Scope.settings,
        default="",
    )

    show_question_header = Boolean(
        display_name=_('Show "Problem" heading'),
        help=_('Display the heading "Problem" above the problem text?'),
        scope=Scope.settings,
        default=True,
    )

    weight = Float(
        display_name=_("Weight"),
        help=_("The maximum score the learner can receive for the problem"),
        scope=Scope.settings,
        default=1,
    )

    item_background_color = String(
        display_name=_("Item background color"),
        help=_("The background color of draggable items in the problem."),
        scope=Scope.settings,
        default="",
    )

    item_text_color = String(
        display_name=_("Item text color"),
        help=_("Text color to use for draggable items."),
        scope=Scope.settings,
        default="",
    )

    data = Dict(
        display_name=_("Problem data"),
        help=_(
            "Information about zones, items, feedback, and background image for this problem. "
            "This information is derived from the input that a course author provides via the interactive editor "
            "when configuring the problem."
        ),
        scope=Scope.content,
        default=DEFAULT_DATA,
    )

    item_state = Dict(
        help=_("Information about current positions of items that a learner has dropped on the target image."),
        scope=Scope.user_state,
        default={},
    )

    attempts = Integer(
        help=_("Number of attempts learner used"),
        scope=Scope.user_state,
        default=0
    )

    completed = Boolean(
        help=_("Indicates whether a learner has completed the problem at least once"),
        scope=Scope.user_state,
        default=False,
    )

    grade = Float(
        help=_("Keeps maximum achieved score by student"),
        scope=Scope.user_state,
        default=0
    )

    block_settings_key = 'drag-and-drop-v2'
    has_score = True

    @XBlock.supports("multi_device")  # Enable this block for use in the mobile app via webview
    def student_view(self, context):
        """
        Player view, displayed to the student
        """

        fragment = Fragment()
        fragment.add_content(loader.render_template('/templates/html/drag_and_drop.html'))
        css_urls = (
            'public/css/vendor/jquery-ui-1.10.4.custom.min.css',
            'public/css/drag_and_drop.css'
        )
        js_urls = (
            'public/js/vendor/jquery-ui-1.10.4.custom.min.js',
            'public/js/vendor/jquery-ui-touch-punch-0.2.3.min.js',  # Makes it work on touch devices
            'public/js/vendor/virtual-dom-1.3.0.min.js',
            'public/js/drag_and_drop.js',
        )
        for css_url in css_urls:
            fragment.add_css_url(self.runtime.local_resource_url(self, css_url))
        for js_url in js_urls:
            fragment.add_javascript_url(self.runtime.local_resource_url(self, js_url))

        self.include_theme_files(fragment)

        fragment.initialize_js('DragAndDropBlock', self.get_configuration())

        return fragment

    def get_configuration(self):
        """
        Get the configuration data for the student_view.
        The configuration is all the settings defined by the author, except for correct answers
        and feedback.
        """

        def items_without_answers():
            """
            Removes feedback and answer from items
            """
            items = copy.deepcopy(self.data.get('items', ''))
            for item in items:
                del item['feedback']
                # Use item.pop to remove both `item['zone']` and `item['zones']`; we don't have
                # a guarantee that either will be present, so we can't use `del`. Legacy instances
                # will have `item['zone']`, while current versions will have `item['zones']`.
                item.pop('zone', None)
                item.pop('zones', None)
                # Fall back on "backgroundImage" to be backward-compatible.
                image_url = item.get('imageURL') or item.get('backgroundImage')
                if image_url:
                    item['expandedImageURL'] = self._expand_static_url(image_url)
                else:
                    item['expandedImageURL'] = ''
            return items

        return {
            "mode": self.mode,
            "max_attempts": self.max_attempts,
            "zones": self._get_zones(),
            # SDK doesn't supply url_name.
            "url_name": getattr(self, 'url_name', ''),
            "display_zone_labels": self.data.get('displayLabels', False),
            "display_zone_borders": self.data.get('displayBorders', False),
            "items": items_without_answers(),
            "title": self.display_name,
            "show_title": self.show_title,
            "problem_text": self.question_text,
            "show_problem_header": self.show_question_header,
            "target_img_expanded_url": self.target_img_expanded_url,
            "target_img_description": self.target_img_description,
            "item_background_color": self.item_background_color or None,
            "item_text_color": self.item_text_color or None,
            # final feedback (data.feedback.finish) is not included - it may give away answers.
        }

    def studio_view(self, context):
        """
        Editing view in Studio
        """

        js_templates = loader.load_unicode('/templates/html/js_templates.html')
        help_texts = {
            field_name: self.ugettext(field.help)
            for field_name, field in self.fields.viewitems() if hasattr(field, "help")
        }
        field_values = {
            field_name: field.values
            for field_name, field in self.fields.viewitems() if hasattr(field, "values")
        }
        context = {
            'js_templates': js_templates,
            'help_texts': help_texts,
            'field_values': field_values,
            'self': self,
            'data': urllib.quote(json.dumps(self.data)),
        }

        fragment = Fragment()
        fragment.add_content(loader.render_template('/templates/html/drag_and_drop_edit.html', context))

        css_urls = (
            'public/css/vendor/jquery-ui-1.10.4.custom.min.css',
            'public/css/drag_and_drop_edit.css'
        )
        js_urls = (
            'public/js/vendor/jquery-ui-1.10.4.custom.min.js',
            'public/js/vendor/handlebars-v1.1.2.js',
            'public/js/drag_and_drop_edit.js',
        )
        for css_url in css_urls:
            fragment.add_css_url(self.runtime.local_resource_url(self, css_url))
        for js_url in js_urls:
            fragment.add_javascript_url(self.runtime.local_resource_url(self, js_url))

        # Do a bit of manipulation so we get the appearance of a list of zone options on
        # items that still have just a single zone stored

        items = self.data.get('items', [])

        for item in items:
            zones = self._get_item_zones(item['id'])
            # Note that we appear to be mutating the state of the XBlock here, but because
            # the change won't be committed, we're actually just affecting the data that
            # we're going to send to the client, not what's saved in the backing store.
            item['zones'] = zones
            item.pop('zone', None)

        fragment.initialize_js('DragAndDropEditBlock', {
            'data': self.data,
            'target_img_expanded_url': self.target_img_expanded_url,
            'default_background_image_url': self.default_background_image_url,
        })

        return fragment

    @XBlock.json_handler
    def studio_submit(self, submissions, suffix=''):
        """
        Handles studio save.
        """
        self.display_name = submissions['display_name']
        self.mode = submissions['mode']
        self.max_attempts = submissions['max_attempts']
        self.show_title = submissions['show_title']
        self.question_text = submissions['problem_text']
        self.show_question_header = submissions['show_problem_header']
        self.weight = float(submissions['weight'])
        self.item_background_color = submissions['item_background_color']
        self.item_text_color = submissions['item_text_color']
        self.data = submissions['data']

        return {
            'result': 'success',
        }

    @XBlock.json_handler
    def drop_item(self, item_attempt, suffix=''):
        """
        Handles dropping item into a zone.
        """
        self._validate_drop_item(item_attempt)

        if self.mode == self.ASSESSMENT_MODE:
            return self._drop_item_assessment(item_attempt)
        elif self.mode == self.STANDARD_MODE:
            return self._drop_item_standard(item_attempt)
        else:
            raise JsonHandlerError(
                500,
                self.i18n_service.gettext("Unknown DnDv2 mode {mode} - course is misconfigured").format(self.mode)
            )

    @XBlock.json_handler
    def do_attempt(self, data, suffix=''):
        """
        Checks submitted solution and returns feedback.

        Raises 400 error in standard mode.
        """
        self._validate_do_attempt()

        self.attempts += 1
        self._mark_complete_and_publish_grade()

        overall_feedback_msgs, misplaced_ids = self._get_do_attempt_feedback()
        misplaced_items = [self._get_item_definition(int(item_id)) for item_id in misplaced_ids]
        feedback_msgs = [item['feedback']['incorrect'] for item in misplaced_items]

        for item_id in misplaced_ids:
            del self.item_state[item_id]

        return {
            'correct': self._is_correct_answer(),
            'attempts': self.attempts,
            'misplaced_items': list(misplaced_ids),
            'feedback': self._suppress_empty_messages(feedback_msgs),
            'overall_feedback': self._suppress_empty_messages(overall_feedback_msgs)
        }

    @XBlock.json_handler
    def publish_event(self, data, suffix=''):
        """
        Handler to publish XBlock event from frontend
        """
        try:
            event_type = data.pop('event_type')
        except KeyError:
            return {'result': 'error', 'message': 'Missing event_type in JSON data'}

        self.runtime.publish(self, event_type, data)
        return {'result': 'success'}

    @XBlock.json_handler
    def reset(self, data, suffix=''):
        """
        Resets problem to initial state
        """
        self.item_state = {}
        return self._get_user_state()

    @XBlock.json_handler
    def expand_static_url(self, url, suffix=''):
        """ AJAX-accessible handler for expanding URLs to static [image] files """
        return {'url': self._expand_static_url(url)}

    @property
    def i18n_service(self):
        """ Obtains translation service """
        i18n_service = self.runtime.service(self, "i18n")
        if i18n_service:
            return i18n_service
        else:
            return DummyTranslationService()

    @property
    def target_img_expanded_url(self):
        """ Get the expanded URL to the target image (the image items are dragged onto). """
        if self.data.get("targetImg"):
            return self._expand_static_url(self.data["targetImg"])
        else:
            return self.default_background_image_url

    @property
    def target_img_description(self):
        """ Get the description for the target image (the image items are dragged onto). """
        return self.data.get("targetImgDescription", "")

    @property
    def default_background_image_url(self):
        """ The URL to the default background image, shown when no custom background is used """
        return self.runtime.local_resource_url(self, "public/img/triangle.png")

    @property
    def attempts_remain(self):
        """
        Checks if current student still have more attempts.
        """
        return self.max_attempts is None or self.max_attempts == 0 or self.attempts < self.max_attempts

    @XBlock.handler
    def get_user_state(self, request, suffix=''):
        """ GET all user-specific data, and any applicable feedback """
        data = self._get_user_state()

        return webob.Response(body=json.dumps(data), content_type='application/json')

    def _validate_do_attempt(self):
        """
        Validates if `do_attempt` handler should be executed
        """
        if self.mode != self.ASSESSMENT_MODE:
            raise JsonHandlerError(
                400,
                self.i18n_service.gettext("do_attempt handler should only be called for assessment mode")
            )
        if not self.attempts_remain:
            raise JsonHandlerError(
                409,
                self.i18n_service.gettext("Max number of attempts reached")
            )

    def _get_do_attempt_feedback(self):
        """
        Returns feedback for `do_attempt` handler.
        """
        required_ids, placed_ids, correct_ids = self._get_item_raw_stats()
        missing_ids = required_ids - placed_ids
        misplaced_ids = placed_ids - correct_ids

        feedback_msgs = []

        def _add_msg_if_exists(ids_list, message):
            """ Adds message to feedback messages if corresponding items list is not empty """
            if ids_list:
                feedback_msgs.append(message(len(ids_list), self.i18n_service.ngettext))

        _add_msg_if_exists(correct_ids, FeedbackMessages.correctly_placed)
        _add_msg_if_exists(misplaced_ids, FeedbackMessages.misplaced)
        _add_msg_if_exists(missing_ids, FeedbackMessages.not_placed)

        if misplaced_ids and self.attempts_remain:
            feedback_msgs.append(FeedbackMessages.MISPLACED_ITEMS_RETURNED)

        overall_feedback_key = 'start' if self.attempts_remain and (misplaced_ids or missing_ids) else 'finish'
        feedback_msgs.append(self.data['feedback'][overall_feedback_key])

        if not self.attempts_remain:
            feedback_msgs.append(FeedbackMessages.FINAL_ATTEMPT_TPL.format(score=self.grade))

        return feedback_msgs, misplaced_ids

    def _drop_item_standard(self, item_attempt):
        """
        Handles dropping item to a zone in standard mode.
        """
        item = self._get_item_definition(item_attempt['val'])

        is_correct = self._is_attempt_correct(item_attempt)  # Student placed item in a correct zone
        if is_correct:  # In standard mode state is only updated when attempt is correct
            self.item_state[str(item['id'])] = self._make_state_from_attempt(item_attempt, is_correct)

        self._mark_complete_and_publish_grade()
        self._publish_item_dropped_event(item_attempt, is_correct)

        item_feedback_key = 'correct' if is_correct else 'incorrect'
        item_feedback = item['feedback'][item_feedback_key]
        overall_feedback = self.data['feedback']['finish'] if self._is_correct_answer() else None

        return {
            'correct': is_correct,
            'finished': self._is_correct_answer(),
            'overall_feedback': self._suppress_empty_messages([overall_feedback]),
            'feedback': self._suppress_empty_messages([item_feedback])
        }

    def _drop_item_assessment(self, item_attempt):
        """
        Handles dropping item into a zone in assessment mode
        """
        if not self.attempts_remain:
            raise JsonHandlerError(409, self.i18n_service.gettext("Max number of attempts reached"))

        item = self._get_item_definition(item_attempt['val'])

        is_correct = self._is_attempt_correct(item_attempt)
        # State is always updated in assessment mode to store intermediate item positions
        self.item_state[str(item['id'])] = self._make_state_from_attempt(item_attempt, is_correct)

        self._publish_item_dropped_event(item_attempt, is_correct)

        return {}

    def _validate_drop_item(self, item):
        """
        Validates `drop_item` parameters
        """
        zone = self._get_zone_by_uid(item['zone'])
        if not zone:
            raise JsonHandlerError(400, "Item zone data invalid.")

    @staticmethod
    def _suppress_empty_messages(messages):
        """
        Filters out empty messages from the list.
        """
        return [msg for msg in messages if msg]

    @staticmethod
    def _make_state_from_attempt(attempt, correct):
        """
        Converts "attempt" data coming from browser into "state" entry stored in item_state
        """
        return {
            'zone': attempt['zone'],
            'correct': correct,
            'x_percent': attempt['x_percent'],
            'y_percent': attempt['y_percent'],
        }

    def _mark_complete_and_publish_grade(self):
        """
        Helper method to update `self.comnpleted` and submit grade event if appropriate conditions met.
        """
        if not self.completed or (self.mode == self.ASSESSMENT_MODE and not self.attempts_remain):
            self.completed = self._is_correct_answer() or not self.attempts_remain
            grade = self._get_grade()
            if grade > self.grade:
                self.grade = grade
                self._publish_grade()

    def _publish_grade(self):
        """
        Publishes grade
        """
        try:
            self.runtime.publish(self, 'grade', {
                'value': self.grade,
                'max_value': self.weight,
            })
        except NotImplementedError:
            # Note, this publish method is unimplemented in Studio runtimes,
            # so we have to figure that we're running in Studio for now
            pass

    def _publish_item_dropped_event(self, attempt, is_correct):
        """
        Publishes item dropped event.
        """
        item = self._get_item_definition(attempt['val'])
        # attempt should already be validated here - not doing the check for existing zone again
        zone = self._get_zone_by_uid(attempt['zone'])

        self.runtime.publish(self, 'edx.drag_and_drop_v2.item.dropped', {
            'item_id': item['id'],
            'location': zone.get("title"),
            'location_id': zone.get("uid"),
            'is_correct': is_correct,
        })

    def _is_attempt_correct(self, attempt):
        """
        Check if the item was placed correctly.
        """
        correct_zones = self._get_item_zones(attempt['val'])
        return attempt['zone'] in correct_zones

    def _expand_static_url(self, url):
        """
        This is required to make URLs like '/static/dnd-test-image.png' work (note: that is the
        only portable URL format for static files that works across export/import and reruns).
        This method is unfortunately a bit hackish since XBlock does not provide a low-level API
        for this.
        """
        if hasattr(self.runtime, 'replace_urls'):
            url = self.runtime.replace_urls('"{}"'.format(url))[1:-1]
        elif hasattr(self.runtime, 'course_id'):
            # edX Studio uses a different runtime for 'studio_view' than 'student_view',
            # and the 'studio_view' runtime doesn't provide the replace_urls API.
            try:
                from static_replace import replace_static_urls  # pylint: disable=import-error
                url = replace_static_urls('"{}"'.format(url), None, course_id=self.runtime.course_id)[1:-1]
            except ImportError:
                pass
        return url

    def _get_user_state(self):
        """ Get all user-specific data, and any applicable feedback """
        item_state = self._get_item_state()
        for item_id, item in item_state.iteritems():
            # If information about zone is missing
            # (because problem was completed before a11y enhancements were implemented),
            # deduce zone in which item is placed from definition:
            if item.get('zone') is None:
                valid_zones = self._get_item_zones(int(item_id))
                if valid_zones:
                    # If we get to this point, then the item was placed prior to support for
                    # multiple correct zones being added. As a result, it can only be correct
                    # on a single zone, and so we can trust that the item was placed on the
                    # zone with index 0.
                    item['zone'] = valid_zones[0]
                else:
                    item['zone'] = 'unknown'

            # In assessment mode, if item is placed correctly and than the page is refreshed, "correct"
            # will spill to the frontend, making item "disabled", thus allowing students to obtain answer by trial
            # and error + refreshing the page. In order to avoid that, we remove "correct" from an item here
            if self.mode == self.ASSESSMENT_MODE:
                del item["correct"]

        if self.mode == self.STANDARD_MODE:
            is_finished = self._is_correct_answer()
        else:
            is_finished = not self.attempts_remain

        overall_feedback = [self.data['feedback']['finish' if is_finished else 'start']]

        return {
            'items': item_state,
            'finished': is_finished,
            'attempts': self.attempts,
            'overall_feedback': self._suppress_empty_messages(overall_feedback),
        }

    def _get_item_state(self):
        """
        Returns a copy of the user item state.
        Converts to a dict if data is stored in legacy tuple form.
        """

        # IMPORTANT: this method should always return a COPY of self.item_state - it is called from get_user_state
        # handler and manipulated there to hide correctness of items placed
        state = {}

        for item_id, item in self.item_state.iteritems():
            if isinstance(item, dict):
                state[item_id] = item.copy()  # items are manipulated in _get_user_state, so we protect actual data
            else:
                state[item_id] = {'top': item[0], 'left': item[1]}

        return state

    def _get_item_definition(self, item_id):
        """
        Returns definition (settings) for item identified by `item_id`.
        """
        return next(i for i in self.data['items'] if i['id'] == item_id)

    def _get_item_zones(self, item_id):
        """
        Returns a list of the zones that are valid options for the item.

        If the item is configured with a list of zones, return that list. If
        the item is configured with a single zone, encapsulate that zone's
        ID in a list and return the list. If the item is not configured with
        any zones, or if it's configured explicitly with no zones, return an
        empty list.
        """
        item = self._get_item_definition(item_id)
        if item.get('zones') is not None:
            return item.get('zones')
        elif item.get('zone') is not None and item.get('zone') != 'none':
            return [item.get('zone')]
        else:
            return []

    def _get_zones(self):
        """
        Get drop zone data, defined by the author.
        """
        # Convert zone data from old to new format if necessary
        zones = []
        for zone in self.data.get('zones', []):
            zone = zone.copy()
            if "uid" not in zone:
                zone["uid"] = zone.get("title")  # Older versions used title as the zone UID
            # Remove old, now-unused zone attributes, if present:
            zone.pop("id", None)
            zone.pop("index", None)
            zones.append(zone)
        return zones

    def _get_zone_by_uid(self, uid):
        """
        Given a zone UID, return that zone, or None.
        """
        for zone in self._get_zones():
            if zone["uid"] == uid:
                return zone

    def _get_item_stats(self):
        """
        Returns a tuple representing the number of correctly-placed items,
        and the total number of items that must be placed on the board (non-decoy items).
        """
        required_items, __, correct_items = self._get_item_raw_stats()

        return len(correct_items), len(required_items)

    def _get_item_raw_stats(self):
        """
        Returns a 3-tuple containing required, placed and correct items.
        """
        all_items = [str(item['id']) for item in self.data['items']]
        item_state = self._get_item_state()

        required_items = set(item_id for item_id in all_items if self._get_item_zones(int(item_id)) != [])
        placed_items = set(item_id for item_id in all_items if item_id in item_state)
        correct_items = set(item_id for item_id in placed_items if item_state[item_id]['correct'])

        return required_items, placed_items, correct_items

    def _get_grade(self):
        """
        Returns the student's grade for this block.
        """
        correct_count, required_count = self._get_item_stats()
        return correct_count / float(required_count) * self.weight

    def _is_correct_answer(self):
        """
        All items are at their correct place and a value has been
        submitted for each item that expects a value.
        """
        correct_count, required_count = self._get_item_stats()
        return correct_count == required_count

    @staticmethod
    def workbench_scenarios():
        """
        A canned scenario for display in the workbench.
        """
        return [("Drag-and-drop-v2 scenario", "<vertical_demo><drag-and-drop-v2/></vertical_demo>")]
