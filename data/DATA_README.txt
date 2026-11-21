IS THE NEW PROMPT BETTER? DATA

questions.csv contains 300 customer questions, one per row, each with two answers.

Columns
  id              Question number, for example Q-001
  topic           orders, refunds, account, shipping, or product
  question        What the customer asked
  answer_current  The answer from the version of the assistant that is live today
  answer_new      The answer from the proposed new version

The file is UTF-8 and uses standard CSV quoting.

Output
Alongside your report, produce a file named verdicts.csv with one row per question:
  id, better
where better is "current", "new", or "tie".
