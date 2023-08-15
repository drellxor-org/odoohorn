FROM odoo:16 as builder

USER root

COPY ./requirements.txt /
RUN pip install -r requirements.txt

RUN mkdir -p /var/lib/odoo/.local/lib && chown -R odoo /var/lib/odoo/.local/lib \
  && mkdir -p /var/lib/odoo/.local/_pydevd_bundle && chown -R odoo /var/lib/odoo/.local/_pydevd_bundle \
  && mkdir -p /var/lib/odoo/.local/_pydevd_frame_eval && chown -R odoo /var/lib/odoo/.local/_pydevd_frame_eval \
  && mkdir -p /var/lib/odoo/.local/pydevd_attach_to_process && chown -R odoo /var/lib/odoo/.local/pydevd_attach_to_process \
  && mkdir -p /var/lib/odoo/.local/bin && chown -R odoo /var/lib/odoo/.local/bin

RUN chown -R odoo /usr/lib/python3/dist-packages/odoo

FROM builder as runner

ARG RUNNING_ENV
ENV RUNNING_ENV=${RUNNING_ENV}

COPY --chown=odoo ./entrypoint.sh /
COPY --chown=odoo ./config/${RUNNING_ENV}/odoo.conf /etc/odoo
COPY --chown=odoo ./addons /mnt/extra-addons

RUN ["chmod", "+x", "./entrypoint.sh"]

USER odoo

ENTRYPOINT /entrypoint.sh odoo