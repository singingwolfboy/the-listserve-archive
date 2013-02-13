from collections import namedtuple
import datetime
import urllib

import pytz


class Post(namedtuple('Post', ['subject', 'author', 'body', 'date'])):
    """Represents a single Listserve email post.

    subject, author, and body are unicode strings.
    date is a 3-tuple of ints: (year, month, day).

    Posts are json-serializable.
    """

    def __new__(cls, subject, author, body, date):
        #If date is a list, make it a tuple.
        #This makes post == Post(*json.loads(json.dumps(post))).
        if isinstance(date, list):
            date = tuple(date)

        return super(cls, Post).__new__(
            cls,
            subject,
            author,
            body,
            date)

    @staticmethod
    def from_cio_message(message):
        """Post factory from a Context.IO message (with body).

        See http://context.io/docs/2.0/accounts/messages (and
        _include_body_)."""

        subject = message['subject']

        m_from = message['addresses']['from']
        author = m_from['name'] if 'name' in m_from else 'Anonymous'

        body = message['body'][0]['content']  # TL sends one plaintext body.
        #Remove unsubscribe text.
        body = body[:body.rfind('--')]

        date = datetime.datetime.fromtimestamp(message['date'])
        #This is a hack. Apparently, the posts aren't sent out automatically,
        #but manually sent on a schedule aligned with EST. We can count
        #on not getting more than one post in a day, but the definition of
        #day aligns with EST. Convert to EST and allow for a few hours of
        #leeway past midnight.
        eastern = pytz.timezone("US/Eastern")
        date = eastern.localize(date)
        date = date - datetime.timedelta(hours=4)
        date = (date.year, date.month, date.day)

        return Post(subject, author, body, date)

    def datestr(self):
        """Return the date of this Post as 'YYYY-MM-DD'."""
        strs = [str(i) for i in self.date]

        #Prepend 0s where needed, assuming year is length 4.
        return '-'.join('0' * (2 - len(s)) + s for s in strs)

    def to_jekyll_html(self):
        """Return a Jekyll post as (filename, contents)."""

        #Build a readable datestr, eg 'August 02 2012'.
        date = datetime.date(*self.date)
        full_month_datestr = date.strftime("%B %d %Y")

        #Cut out Listserve subject header.
        title = self.subject.replace('[The Listserve]', '').strip()
        if not title:
            title = '[no subject]'
        desc = 'A post from The Listserve'  # TODO do something interesting

        #Jekyll needs the filename as YYYY-MM-DD-title.markup
        #title can be empty, but we still need the '-'
        fname = "{date}-{title}.html".format(
            date=self.datestr(),
            title=urllib.quote_plus(title.encode('utf-8'))
        )

        #Find paragraphs.
        post_text = self.body.replace('\r', '')
        paras = post_text.split(u'\n\n')
        paras = [para.replace('\n', '<br />') for para in paras if para]

        #Build html paragraphs.
        post_text = '\n'.join(
            ["<p>%s</p>" % para.encode('ascii', 'xmlcharrefreplace')
             for para in paras])

        #Encode output and build file contents.
        contents = """---
layout: post
title: "{title}"
description: "{desc}"
---

<h2 id='post-title'>
{{{{ page.title }}}}
</h2>

<p class="meta">{date}</p>

{post_text}""".format(title=title.replace('"', r'\"').encode('utf-8'),
                      desc=desc.replace('"', r'\"').encode('utf-8'),
                      date=full_month_datestr,
                      post_text=post_text
                      )

        return (fname, contents)
