"""A representative excerpt of IRM 21.6.6.2.21 Decedent Account Refunds.

This is used for the offline demo (no PDF upload needed) and as the grounding
source for the mock LLM provider. It is paraphrased/condensed from the public
IRM 21.6.6 procedure for Processing Decedent Account Refunds so the demo runs
end-to-end. Replace by uploading the real IRM PDF to /extract-rules.
"""

SAMPLE_DECEDENT_REFUND_TEXT = """
21.6.6.2.21.2 Processing Decedent Account Refunds

When the IRS receives a Form 1310, Statement of Person Claiming Refund Due a
Deceased Taxpayer, in response to a CP 01H notice or Letter 12C, review the
claim to determine the correct method to release the decedent refund.

If the claimant is a surviving spouse filing an original or amended joint return,
a Form 1310 is not required and the refund may be issued in both names.

If the claimant is a court-appointed personal representative, both the Form 1310
and the court certificate must be received together, even if a court certificate
was previously provided. If the court certificate is not attached, correspond with
the claimant to request the required documentation.

If a -X freeze will be present after the adjustment posts and the case meets the
criteria for a systemic refund, suspend the case until the freeze has posted and
then release the refund.

For a current year refund, if a TC 971 AC 807 procedure applies, input TC 971
AC 807 to release the refund systemically. When the current year processing cycle
has ended, any cycle after that is considered prior year and a manual refund is
required.

When a manual refund is required, Form 1310 should be perfected with the tax year.

If the case is a CII case, there is no need to refile the Form 1310, but leave a
case note documenting the action taken.
"""
