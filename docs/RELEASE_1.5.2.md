# AI Automation Suggester 1.5.2

This patch release polishes warning text shown in persistent notifications after best-effort parser recovery.

## Changed

- Rewords the parser repair warning from technical JSON terminology to: "Provider response needed formatting repair before display. Review the YAML before using it."
- Rewords token-limit truncation warnings to make clear the YAML should be reviewed before use.

## Notes

The integration still keeps the technical parser warning in stored suggestion attributes for troubleshooting. Persistent notifications now use friendlier wording.