# Payment backends

To manage payments, Joanie relies on payment providers. That means we have to
implement interfaces to interact with these providers. This is the purpose of
the `BasePaymentBackend` class which offers generic methods triggered when a
payment succeeded, failed, is aborted or refunded. In this way when implementing
a new interface, we only need to focus on the logic to normalize data
exchanges from the payment provider to Joanie.

We start with the assumption that modern payment providers are based on a
notification webhook system (e.g: Stripe, Paypal or Payplug). So Joanie relies
on this feature to be notified when something happens on the payment provider
(new payment, refund, failure...).

## Reference

All payment backends are declared within `joanie.payment.backends` and must
inherit from `BasePaymentBackend`. This class implements 3 generic methods in
charge of interacting with Joanie core when a payment succeeded, failed,
or is refunded :

- **`_do_on_payment_success(order, payment)`**
- **`_do_on_payment_failure(order)`**
- **`_do_on_refund(amount, proforma_invoice, refund_reference)`**

On the other hand, your payment backend has to implement 5 methods :

- **`create_payment(self, order, billing_address)`**
- **`create_one_click_payment(self, order, billing_address, credit_card_token)`**
- **`handle_notification(self, request)`**
- **`delete_credit_card(self, credit_card)`**
- **`abort_payment(self, payment_id)`**

## How to

### Use payment module from local environment

To work on Joanie in a local environment, we propose two solutions :

#### Use the `DummyPaymentBackend`

In case you do not need to interact with your payment provider, we implemented
a `DummyPaymentBackend` which allows you to use Joanie locally without any
configuration.

#### Use Ngrok to serve joanie on a public url

Since we took for assumption the use of a payment provider with a webhook
notification system, in order to integrate a local joanie instance with your
payment provider, you have to serve your local instance of Joanie on a public
url. To simplify this task, we have integrated a [ngrok](https://ngrok.com)
service within your `docker-compose`.

##### 1. Run ngrok service

  First you have to start the ngrok service and retrieve the freshly created
  public url. The `make ngrok` command does that for you:

  ```bash
  > make ngrok

  Starting joanie_ngrok_1 ... done
  Joanie is accessible on : 
  https://****-**-**-***-***.ngrok.io # Copy this url
  ```

##### 2. Request Joanie API from ngrok public url

  Once Joanie is served from a public url, you just have to call joanie
  from this public url.

In the case of payments api, the notification url is built on the request's
absolute uri. So in order to make payment webhooks working, you have to update the
joanie endpoint in your client project.

## Supported providers

You can find all payment backends at `src/backend/joanie/payment/backends`.

Currently, Joanie supports :

- [Payplug](https://www.payplug.com/)

## Contributing

This project is intended to be community-driven, if you are interesting by Joanie but your payment provider is not yet supported, feel free to [create an issue](https://github.com/openfun/joanie/issues/new?assignees=&labels=&template=Feature_request.md) or submit a pull request in compliance with our [best pratices](https://openfun.gitbooks.io/handbook/content).
