# -*- coding: utf-8 -*-
""" Drag and Drop v2 XBlock - Utils """

def _(text):
    """ Dummy `gettext` replacement to make string extraction tools scrape strings marked for translation """
    return text


def ngettext_fallback(text_singular, text_plural, n):
    """ Dummy `ngettext` replacement to make string extraction tools scrape strings marked for translation """
    if n == 1:
        return text_singular
    else:
        return text_plural


class DummyTranslationService(object):
    """
    Dummy drop-in replacement for i18n XBlock service
    """
    gettext = _
    ngettext = ngettext_fallback


class FeedbackMessages(object):
    """
    Feedback messages collection
    """
    FINAL_ATTEMPT_TPL = _('Final attempt was used, highest score is {score}')
    MISPLACED_ITEMS_RETURNED = _('Misplaced items were returned to item bank.')

    @staticmethod
    def correctly_placed(n, ngettext=ngettext_fallback):
        """
        Formats "correctly placed items" message
        """
        return ngettext(
            'Correctly placed {correct_count} item.',
            'Correctly placed {correct_count} items.',
            n
        ).format(correct_count=n)

    @staticmethod
    def misplaced(n, ngettext=ngettext_fallback):
        """
        Formats "misplaced items" message
        """
        return ngettext(
            'Misplaced {misplaced_count} item.',
            'Misplaced {misplaced_count} items.',
            n
        ).format(misplaced_count=n)

    @staticmethod
    def not_placed(n, ngettext=ngettext_fallback):
        """
        Formats "did not place required items" message
        """
        return ngettext(
            'Did not place {missing_count} required item.',
            'Did not place {missing_count} required items.',
            n
        ).format(missing_count=n)
