from odoo import api, fields, models, _, SUPERUSER_ID


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _cart_update_order_line(self, product_id, quantity, order_line, **kwargs):
        order_line = super()._cart_update_order_line(product_id, quantity, order_line, **kwargs)

        custom_fields = ['machine_serial', 'part_number', 'commentary']
        write_data = {}

        for field in custom_fields:
            if field in kwargs:
                write_data[field] = kwargs[field]

        order_line.write(write_data)
        return order_line

    def _send_order_confirmation_mail(self):
        if not self:
            return

        if self.env.su:
            # sending mail in sudo was meant for it being sent from superuser
            self = self.with_user(SUPERUSER_ID)

        for sale_order in self:
            mail_template = sale_order._get_confirmation_template()

            if not mail_template:
                continue

            mail_template.send_mail(sale_order.id, force_send=True)

            mail_to_company = self.env.ref('order_product_info.mail_template_sale_confirmation_to_company', raise_if_not_found=False)
            if not mail_to_company:
                continue

            mail_to_company.send_mail(sale_order.id, force_send=True)
