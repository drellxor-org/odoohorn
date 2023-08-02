FROM odoo:16

ARG RUNNING_ENV
ENV RUNNING_ENV=${RUNNING_ENV}

COPY --chown=odoo ./entrypoint.sh /
COPY --chown=odoo ./requirements.txt /
COPY --chown=odoo ./config/${RUNNING_ENV}/odoo.conf /etc/odoo

COPY --chown=odoo ./addons /mnt/extra-addons

RUN ["chmod", "+x", "./entrypoint.sh"]
RUN pip install -r requirements.txt

USER odoo

ENTRYPOINT /entrypoint.sh odoo