# -*- coding: utf-8 -*-
#


# Make '_' a no-op so we can scrape strings
def _(text):
    return text


def ngettext(text_singular, text_plural, n):
    if n == 1:
        return text_singular
    else:
        return text_plural


class FeedbackMessages(object):
    FINAL_ATTEMPT_TPL = _('Final attempt was used, highest score is {score}')
    MISPLACED_ITEMS_RETURNED = _('Misplaced items were returned to item bank.')

    CORRECTLY_PLACED_SINGULAR_TPL = _('Correctly placed {correct_count} item.')
    CORRECTLY_PLACED_PLURAL_TPL = _('Correctly placed {correct_count} items.')

    MISPLACED_SINGULAR_TPL = _('Misplaced {misplaced_count} item.')
    MISPLACED_PLURAL_TPL = _('Misplaced {misplaced_count} items.')

    NOT_PLACED_REQUIRED_SINGULAR_TPL = _('Not placed {missing_count} required item.',)
    NOT_PLACED_REQUIRED_PLURAL_TPL = _('Not placed {missing_count} required items.')
