# Support Ticket #4821 — Integration Failing

A customer pasted their configuration into this ticket, and the whole thread was
later ingested into the support knowledge base. This is exactly how secrets and
PII quietly end up inside a vector index.

## Customer details

- Name: Jane Doe
- Email: jane.doe@example.com
- Phone: (555) 123-4567
- Account SSN on file: 123-45-6789

## Their config (pasted verbatim)

```
OPENAI_API_KEY=sk-ABCDEFGHIJKLMNOPQRSTUVWX1234567890
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
api_key = "aBcDeF1234567890GhIjKlMnOp"
```

## Notes

The extracted PDF text also came through with broken encoding: the customer
wrote “itâ€™s not working” and the café name rendered as “CafiÃ©”, with a stray
replacement character � left in the log.
