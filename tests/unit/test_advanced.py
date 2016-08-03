# Imports ###########################################################

import ddt
import json
import mock
import random
import unittest

from xblockutils.resources import ResourceLoader

from drag_and_drop_v2.utils import FeedbackMessages

from ..utils import make_block, TestCaseMixin, generate_max_and_num_attempts


# Globals ###########################################################

loader = ResourceLoader(__name__)


# Classes ###########################################################

class BaseDragAndDropAjaxFixture(TestCaseMixin):
    ZONE_1 = None
    ZONE_2 = None

    FEEDBACK = {
        0: {"correct": None, "incorrect": None},
        1: {"correct": None, "incorrect": None},
        2: {"correct": None, "incorrect": None}
    }

    FINAL_FEEDBACK = None

    FOLDER = None

    def setUp(self):
        self.patch_workbench()
        self.block = make_block()
        initial_settings = self.initial_settings()
        for field in initial_settings:
            setattr(self.block, field, initial_settings[field])
        self.block.data = self.initial_data()

    @classmethod
    def initial_data(cls):
        return json.loads(loader.load_unicode('data/{}/data.json'.format(cls.FOLDER)))

    @classmethod
    def initial_settings(cls):
        return json.loads(loader.load_unicode('data/{}/settings.json'.format(cls.FOLDER)))

    @classmethod
    def expected_configuration(cls):
        return json.loads(loader.load_unicode('data/{}/config_out.json'.format(cls.FOLDER)))

    @classmethod
    def initial_feedback(cls):
        """ The initial overall_feedback value """
        return cls.expected_configuration()["initial_feedback"]

    def test_get_configuration(self):
        self.assertEqual(self.block.get_configuration(), self.expected_configuration())


class StandardModeFixture(BaseDragAndDropAjaxFixture):
    """
    Common tests for drag and drop in standard mode
    """
    def test_drop_item_wrong_with_feedback(self):
        item_id, zone_id = 0, self.ZONE_2
        data = {"val": item_id, "zone": zone_id, "x_percent": "33%", "y_percent": "11%"}
        res = self.call_handler(self.DROP_ITEM_HANDLER, data)
        self.assertEqual(res, {
            "overall_feedback": None,
            "finished": False,
            "correct": False,
            "feedback": self.FEEDBACK[item_id]["incorrect"]
        })

    def test_drop_item_wrong_without_feedback(self):
        item_id, zone_id = 2, self.ZONE_1
        data = {"val": item_id, "zone": zone_id, "x_percent": "33%", "y_percent": "11%"}
        res = self.call_handler(self.DROP_ITEM_HANDLER, data)
        self.assertEqual(res, {
            "overall_feedback": None,
            "finished": False,
            "correct": False,
            "feedback": self.FEEDBACK[item_id]["incorrect"]
        })

    def test_drop_item_correct(self):
        item_id, zone_id = 0, self.ZONE_1
        data = {"val": item_id, "zone": zone_id, "x_percent": "33%", "y_percent": "11%"}
        res = self.call_handler(self.DROP_ITEM_HANDLER, data)
        self.assertEqual(res, {
            "overall_feedback": None,
            "finished": False,
            "correct": True,
            "feedback": self.FEEDBACK[item_id]["correct"]
        })

    def test_grading(self):
        published_grades = []

        def mock_publish(self, event, params):
            if event == 'grade':
                published_grades.append(params)
        self.block.runtime.publish = mock_publish

        self.call_handler(self.DROP_ITEM_HANDLER, {
            "val": 0, "zone": self.ZONE_1, "y_percent": "11%", "x_percent": "33%"
        })

        self.assertEqual(1, len(published_grades))
        self.assertEqual({'value': 0.5, 'max_value': 1}, published_grades[-1])

        self.call_handler(self.DROP_ITEM_HANDLER, {
            "val": 1, "zone": self.ZONE_2, "y_percent": "90%", "x_percent": "42%"
        })

        self.assertEqual(2, len(published_grades))
        self.assertEqual({'value': 1, 'max_value': 1}, published_grades[-1])

    def test_drop_item_final(self):
        data = {"val": 0, "zone": self.ZONE_1, "x_percent": "33%", "y_percent": "11%"}
        self.call_handler(self.DROP_ITEM_HANDLER, data)

        expected_state = {
            "items": {
                "0": {"x_percent": "33%", "y_percent": "11%", "correct": True, "zone": self.ZONE_1}
            },
            "finished": False,
            "num_attempts": 0,
            'overall_feedback': self.initial_feedback(),
        }
        self.assertEqual(expected_state, self.call_handler('get_user_state', method="GET"))

        data = {"val": 1, "zone": self.ZONE_2, "x_percent": "22%", "y_percent": "22%"}
        res = self.call_handler(self.DROP_ITEM_HANDLER, data)
        self.assertEqual(res, {
            "overall_feedback": self.FINAL_FEEDBACK,
            "finished": True,
            "correct": True,
            "feedback": self.FEEDBACK[1]["correct"]
        })

        expected_state = {
            "items": {
                "0": {
                    "x_percent": "33%", "y_percent": "11%", "correct": True, "zone": self.ZONE_1,
                },
                "1": {
                    "x_percent": "22%", "y_percent": "22%", "correct": True, "zone": self.ZONE_2,
                }
            },
            "finished": True,
            "num_attempts": 0,
            'overall_feedback': self.FINAL_FEEDBACK,
        }
        self.assertEqual(expected_state, self.call_handler('get_user_state', method="GET"))

    def test_do_attempt_not_available(self):
        """
        Tests that do_attempt handler returns 400 error for standard mode DnDv2
        """
        res = self.call_handler(self.DO_ATTEMPT_HANDLER, expect_json=False)

        self.assertEqual(res.status_code, 400)


@ddt.ddt
class AssessmentModeFixture(BaseDragAndDropAjaxFixture):
    """
    Common tests for drag and drop in assessment mode
    """
    CORRECT_SOLUTION = {}

    @staticmethod
    def _make_submission(item_id, zone_id):
        x_percent, y_percent = str(random.randint(0, 100)) + '%', str(random.randint(0, 100)) + '%'
        data = {"val": item_id, "zone": zone_id, "x_percent": x_percent, "y_percent": y_percent}
        return data

    def _submit_solution(self, solution):
        for item_id, zone_id in solution.iteritems():
            data = self._make_submission(item_id, zone_id)
            self.call_handler(self.DROP_ITEM_HANDLER, data)

    def _submit_complete_solution(self):
        self._submit_solution(self.CORRECT_SOLUTION)

    def _reset_problem(self):
        self.call_handler(self.RESET_HANDLER, data={})
        self.assertEqual(self.block.item_state, {})

    def test_multiple_drop_item(self):
        item_zone_map = {0: self.ZONE_1, 1: self.ZONE_2}
        for item_id, zone_id in item_zone_map.iteritems():
            data = self._make_submission(item_id, zone_id)
            x_percent, y_percent = data['x_percent'], data['y_percent']
            res = self.call_handler(self.DROP_ITEM_HANDLER, data)

            self.assertEqual(res, {})

            expected_item_state = {'zone': zone_id, 'correct': True, 'x_percent': x_percent, 'y_percent': y_percent}

            self.assertIn(str(item_id), self.block.item_state)
            self.assertEqual(self.block.item_state[str(item_id)], expected_item_state)

        # make sure item_state is appended to, not reset
        for item_id in item_zone_map:
            self.assertIn(str(item_id), self.block.item_state)

    # pylint: disable=star-args
    @ddt.data(
        (None, 10, False),
        (0, 12, False),
        *(generate_max_and_num_attempts())
    )
    @ddt.unpack
    def test_do_attempt_validation(self, max_attempts, num_attempts, expect_validation_error):
        self.block.max_attempts = max_attempts
        self.block.num_attempts = num_attempts
        res = self.call_handler(self.DO_ATTEMPT_HANDLER, data={}, expect_json=False)

        if expect_validation_error:
            self.assertEqual(res.status_code, 409)
        else:
            self.assertEqual(res.status_code, 200)

    @ddt.data(*[random.randint(0, 100) for _ in xrange(10)])  # pylint: disable=star-args
    def test_do_attempt_raises_number_of_attempts(self, num_attempts):
        self.block.num_attempts = num_attempts
        self.block.max_attempts = num_attempts + 1

        res = self.call_handler(self.DO_ATTEMPT_HANDLER, data={})
        self.assertEqual(self.block.num_attempts, num_attempts + 1)
        self.assertEqual(res['num_attempts'], self.block.num_attempts)

    def test_do_attempt_correct_mark_complete_and_publish_grade(self):
        self._submit_complete_solution()

        with mock.patch('workbench.runtime.WorkbenchRuntime.publish', mock.Mock()) as patched_publish:
            self.call_handler(self.DO_ATTEMPT_HANDLER, data={})

            self.assertTrue(self.block.completed)
            patched_publish.assert_called_once_with(self.block, 'grade', {
                'value': self.block.weight,
                'max_value': self.block.weight,
            })

    def test_do_attempt_incorrect_publish_grade(self):
        correctness = self._submit_partial_solution()

        with mock.patch('workbench.runtime.WorkbenchRuntime.publish', mock.Mock()) as patched_publish:
            self.call_handler(self.DO_ATTEMPT_HANDLER, data={})

            self.assertFalse(self.block.completed)
            patched_publish.assert_called_once_with(self.block, 'grade', {
                'value': self.block.weight * correctness,
                'max_value': self.block.weight,
            })

    def test_do_attempt_post_correct_no_publish_grade(self):
        for item_id, zone_id in self.CORRECT_SOLUTION.iteritems():
            data = self._make_submission(item_id, zone_id)
            self.call_handler(self.DROP_ITEM_HANDLER, data)

        self.call_handler(self.DO_ATTEMPT_HANDLER, data={})  # sets self.complete

        self._reset_problem()

        with mock.patch('workbench.runtime.WorkbenchRuntime.publish', mock.Mock()) as patched_publish:
            self.call_handler(self.DO_ATTEMPT_HANDLER, data={})

            self.assertTrue(self.block.completed)
            self.assertFalse(patched_publish.called)

    def test_do_attempt_incorrect_final_attempt_publish_grade(self):
        self.block.max_attempts = 5
        self.block.num_attempts = 4

        correctness = self._submit_partial_solution()
        expected_grade = self.block.weight * correctness

        with mock.patch('workbench.runtime.WorkbenchRuntime.publish', mock.Mock()) as patched_publish:
            res = self.call_handler(self.DO_ATTEMPT_HANDLER, data={})

            self.assertTrue(self.block.completed)
            patched_publish.assert_called_once_with(self.block, 'grade', {
                'value': expected_grade,
                'max_value': self.block.weight,
            })

            expected_grade_feedback = FeedbackMessages.FINAL_ATTEMPT_TPL.format(score=expected_grade)
            self.assertIn(expected_grade_feedback, res['feedback'])

    def test_do_attempt_misplaced_ids(self):
        misplaced_ids = self._submit_incorrect_solution()

        res = self.call_handler(self.DO_ATTEMPT_HANDLER, data={})
        self.assertTrue(res['misplaced_items'], misplaced_ids)
        self.assertIn(FeedbackMessages.MISPLACED_ITEMS_RETURNED, res['feedback'])


class TestDragAndDropHtmlData(StandardModeFixture, unittest.TestCase):
    FOLDER = "html"

    ZONE_1 = "Zone <i>1</i>"
    ZONE_2 = "Zone <b>2</b>"

    FEEDBACK = {
        0: {"correct": "Yes <b>1</b>", "incorrect": "No <b>1</b>"},
        1: {"correct": "Yes <i>2</i>", "incorrect": "No <i>2</i>"},
        2: {"correct": "", "incorrect": ""}
    }

    FINAL_FEEDBACK = "Final <strong>feedback</strong>!"


class TestDragAndDropPlainData(StandardModeFixture, unittest.TestCase):
    FOLDER = "plain"

    ZONE_1 = "zone-1"
    ZONE_2 = "zone-2"

    FEEDBACK = {
        0: {"correct": "Yes 1", "incorrect": "No 1"},
        1: {"correct": "Yes 2", "incorrect": "No 2"},
        2: {"correct": "", "incorrect": ""}
    }

    FINAL_FEEDBACK = "This is the final feedback."


class TestOldDataFormat(TestDragAndDropPlainData):
    """
    Make sure we can work with the slightly-older format for 'data' field values.
    """
    FOLDER = "old"
    FINAL_FEEDBACK = "Final Feed"

    ZONE_1 = "Zone 1"
    ZONE_2 = "Zone 2"


class TestDragAndDropAssessmentData(AssessmentModeFixture, unittest.TestCase):
    FOLDER = "assessment"

    ZONE_1 = "zone-1"
    ZONE_2 = "zone-2"

    CORRECT_SOLUTION = {
        0: ZONE_1,
        1: ZONE_2
    }

    FEEDBACK = {
        0: {"correct": "Yes 1", "incorrect": "No 1"},
        1: {"correct": "Yes 2", "incorrect": "No 2"},
        2: {"correct": "", "incorrect": ""}
    }

    FINAL_FEEDBACK = "This is the final feedback."

    def _submit_partial_solution(self):
        self._submit_solution({0: self.ZONE_1})
        return 0.5

    def _submit_incorrect_solution(self):
        self._submit_solution({0: self.ZONE_2, 1: self.ZONE_1})
        self.call_handler(self.DROP_ITEM_HANDLER, self._make_submission(1, self.ZONE_1))
        self.call_handler(self.DROP_ITEM_HANDLER, self._make_submission(0, self.ZONE_2))
        return 0, 1

    def test_do_attempt_feedback_incorrect(self):
        self._submit_solution({0: self.ZONE_2, 1: self.ZONE_1})

        res = self.call_handler(self.DO_ATTEMPT_HANDLER, data={})
        expected_misplaced = FeedbackMessages.MISPLACED_PLURAL_TPL.format(misplaced_count=2)
        self.assertIn(expected_misplaced, res['feedback'])

    def test_do_attempt_feedback_incorrect_not_placed(self):
        self._submit_solution({0: self.ZONE_2})
        res = self.call_handler(self.DO_ATTEMPT_HANDLER, data={})
        expected_misplaced = FeedbackMessages.MISPLACED_SINGULAR_TPL.format(misplaced_count=1)
        expected_not_placed = FeedbackMessages.NOT_PLACED_REQUIRED_SINGULAR_TPL.format(missing_count=1)
        self.assertIn(expected_misplaced, res['feedback'])
        self.assertIn(expected_not_placed, res['feedback'])

    def test_do_attempt_feedback_not_placed(self):
        res = self.call_handler(self.DO_ATTEMPT_HANDLER, data={})
        expected_not_placed = FeedbackMessages.NOT_PLACED_REQUIRED_PLURAL_TPL.format(missing_count=2)
        self.assertIn(expected_not_placed, res['feedback'])

    def test_do_attempt_feedback_correct_and_decoy(self):
        self._submit_solution({0: self.ZONE_1, 1:self.ZONE_2, 2: self.ZONE_2})  # incorrect solution - decoy placed
        res = self.call_handler(self.DO_ATTEMPT_HANDLER, data={})
        expected_misplaced = FeedbackMessages.MISPLACED_SINGULAR_TPL.format(misplaced_count=1)
        expected_correct = FeedbackMessages.CORRECTLY_PLACED_PLURAL_TPL.format(correct_count=2)
        self.assertIn(expected_misplaced, res['feedback'])
        self.assertIn(expected_correct, res['feedback'])
        self.assertIn(FeedbackMessages.MISPLACED_ITEMS_RETURNED, res['feedback'])

    def test_do_attempt_feedback_correct(self):
        self._submit_solution({0: self.ZONE_1, 1: self.ZONE_2})  # correct solution
        res = self.call_handler(self.DO_ATTEMPT_HANDLER, data={})
        expected_correct = FeedbackMessages.CORRECTLY_PLACED_PLURAL_TPL.format(correct_count=2)
        self.assertIn(expected_correct, res['feedback'])
        self.assertNotIn(FeedbackMessages.MISPLACED_ITEMS_RETURNED, res['feedback'])

    def test_do_attempt_feedback_partial(self):
        self._submit_solution({0: self.ZONE_1})  # partial solution
        res = self.call_handler(self.DO_ATTEMPT_HANDLER, data={})
        expected_correct = FeedbackMessages.CORRECTLY_PLACED_SINGULAR_TPL.format(correct_count=1)
        expected_missing = FeedbackMessages.NOT_PLACED_REQUIRED_SINGULAR_TPL.format(missing_count=1)
        self.assertIn(expected_correct, res['feedback'])
        self.assertIn(expected_missing, res['feedback'])
        self.assertNotIn(FeedbackMessages.MISPLACED_ITEMS_RETURNED, res['feedback'])
