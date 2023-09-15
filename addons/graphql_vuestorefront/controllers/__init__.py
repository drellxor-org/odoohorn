from . import main

# Implemented for frontend  purpose
import werkzeug
import odoo.http as http


class HttpDispatcherDebug(http.HttpDispatcher):
    def pre_dispatch(self, rule, args):
        routing = rule.endpoint.routing
        self.request.session.can_save = routing.get('save_session', True)

        set_header = self.request.future_response.headers.set
        cors = routing.get('cors')
        if cors:
            origin_header = self.request.httprequest.headers.get('Origin') or ''
            referer_header = self.request.httprequest.headers.get('Referer') or ''

            if origin_header:
                set_header('Access-Control-Allow-Origin', origin_header)
            elif referer_header:
                set_header('Access-Control-Allow-Origin', referer_header)

            if 'Access-Control-Allow-Origin' not in self.request.future_response.headers:
                set_header('Access-Control-Allow-Origin', cors)
            set_header('Access-Control-Allow-Methods', (
                'POST' if routing['type'] == 'json'
                else ', '.join(routing['methods'] or ['GET', 'POST'])
            ))

        if cors and self.request.httprequest.method == 'OPTIONS':
            set_header('Access-Control-Max-Age', http.CORS_MAX_AGE)
            set_header('Access-Control-Allow-Headers',
                       'Origin, X-Requested-With, Content-Type, Accept, Authorization')
            werkzeug.exceptions.abort(http.Response(status=204))


def _save_session(self):
    """ Save a modified session on disk. """
    sess = self.session

    if not sess.can_save:
        return

    if sess.should_rotate:
        sess['_geoip'] = self.geoip
        http.root.session_store.rotate(sess, self.env)  # it saves
    elif sess.is_dirty:
        sess['_geoip'] = self.geoip
        http.root.session_store.save(sess)

    # We must not set the cookie if the session id was specified
    # using a http header or a GET parameter.
    # There are two reasons to this:
    # - When using one of those two means we consider that we are
    #   overriding the cookie, which means creating a new session on
    #   top of an already existing session and we don't want to
    #   create a mess with the 'normal' session (the one using the
    #   cookie). That is a special feature of the Javascript Session.
    # - It could allow session fixation attacks.
    cookie_sid = self.httprequest.cookies.get('session_id')
    if not sess.is_explicit and (sess.is_dirty or cookie_sid != sess.sid):
        self.future_response.set_cookie('session_id', sess.sid,
                                        max_age=http.SESSION_LIFETIME,
                                        httponly=True,
                                        samesite='None',
                                        secure=True)


http.Request._save_session = _save_session
http._dispatchers['http'] = HttpDispatcherDebug
