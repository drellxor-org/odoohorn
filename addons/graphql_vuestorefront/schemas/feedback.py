import graphene


class SendFeedback(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String()
        phone = graphene.String()
        text = graphene.String()

    response_message = graphene.String()

    @staticmethod
    def mutate(self, info, name, email, phone, text):
        env = info.context['env']
        website = env['website'].get_current_website()
        feedback_model = env['feedback'].sudo()

        feedback_model.create({
            'name': name,
            'email': email,
            'phone': phone,
            'text': text,
            'website': website.id
        })

        return SendFeedback(response_message='OK')


class FeedbackMutation(graphene.ObjectType):
    send_feedback = SendFeedback.Field(description="Send Feedback")
