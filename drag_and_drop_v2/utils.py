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