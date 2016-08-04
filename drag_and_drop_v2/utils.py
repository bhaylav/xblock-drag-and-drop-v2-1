# -*- coding: utf-8 -*-
#


# Make '_' a no-op so we can scrape strings
def _(text):
    return text


def ngettext_fallback(text_singular, text_plural, n):
    if n == 1:
        return text_singular
    else:
        return text_plural


class DummyTranslationService(object):
    gettext = _
    ngettext = ngettext_fallback


class FeedbackMessages(object):
    FINAL_ATTEMPT_TPL = _('Final attempt was used, highest score is {score}')
    MISPLACED_ITEMS_RETURNED = _('Misplaced items were returned to item bank.')

    @staticmethod
    def correctly_placed(n, ngettext=ngettext_fallback):
        return ngettext(
            'Correctly placed {correct_count} item.',
            'Correctly placed {correct_count} items.',
            n
        ).format(correct_count=n)

    @staticmethod
    def misplaced(n, ngettext=ngettext_fallback):
        return ngettext(
            'Misplaced {misplaced_count} item.',
            'Misplaced {misplaced_count} items.',
            n
        ).format(misplaced_count=n)

    @staticmethod
    def not_placed(n, ngettext=ngettext_fallback):
        return ngettext(
            'Did not place {missing_count} required item.',
            'Did not place {missing_count} required items.',
            n
        ).format(missing_count=n)
