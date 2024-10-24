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
- **`_do_on_refund(amount, invoice, refund_reference, installment_id)`**

On the other hand, your payment backend has to implement 5 methods :

- **`create_payment(self, order, billing_address)`**
- **`create_one_click_payment(self, order, billing_address, credit_card_token)`**
- **`handle_notification(self, request)`**
- **`delete_credit_card(self, credit_card)`**
- **`abort_payment(self, payment_id)`**

If the payment backend (such as Lyra) supports zero-click payment, you can
implement the `create_zero_click_payment` method.
This method is called when the user has already saved its credit card and
when a payment schedule exists for an order.

## How to

### Use payment module from local environment

To work on Joanie in a local environment, we propose two solutions :

#### Use the `DummyPaymentBackend`

In case you do not need to interact with your payment provider, we implemented
a `DummyPaymentBackend` which allows you to use Joanie locally without any
configuration.

#### Use localtunnel to serve joanie on a public url

Since we took for assumption the use of a payment provider with a webhook
notification system, in order to integrate a local joanie instance with your
payment provider, you have to serve your local instance of Joanie on a public
url. To simplify this task, we have integrated a [localtunnel](https://theboroer.github.io/localtunnel-www/)

##### 1. Run joanie over localtunnel service

  First you have to start joanie application then open a localtunnel. To ease this step,
  there is a command `tunnel` available in the Makefile. So `make tunnel` will run
  joanie application then open a localtunnel. The process will stay in foreground and will
  print all requests catched by your localtunnel.

  ```bash
  > make tunnel

  [+] Building 0.0s (0/0)                                                docker:desktop-linux
  [+] Running 3/3
   ✔ Container joanie-postgresql-1  Running                                              0.0s
   ✔ Container joanie-app-1         Running                                              0.0s
   ✔ Container joanie-nginx-1       Started                                              0.1s
  ...

  npx localtunnel -s dev-****-joanie -h https://localtunnel.me --port 8071 --print-requests
  your url is: https://dev-****-joanie.loca.lt # Copy this url
  ```

##### 2. Request Joanie API from localtunnel public url

  Once Joanie is served from a public url, you just have to call joanie
  from this public url. The public url has been printed by the `make tunnel` command but
  if you do not see it anymore in our terminal, you can run `bin/get_tunnel_url` at the
  root of the project.
  It follows the pattern `https://dev-{USER}-joanie.loca.lt`.


  In the case of payments api, the notification url is built on the request's
  absolute uri. So in order to make payment webhooks working, you have to update the
  joanie endpoint in your client project.

## Supported providers

You can find all payment backends at `src/backend/joanie/payment/backends`.

Currently, Joanie supports :

- [Payplug](https://www.payplug.com/)
- [Lyra](https://www.lyra.com/)

## Contributing

This project is intended to be community-driven, if you are interesting by Joanie but your payment provider is not yet supported, feel free to [create an issue](https://github.com/openfun/joanie/issues/new?assignees=&labels=&template=Feature_request.md) or submit a pull request in compliance with our [best pratices](https://openfun.gitbooks.io/handbook/content).
