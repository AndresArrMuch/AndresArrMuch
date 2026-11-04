import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
for e in c.execute("select id, entry_number, gloss, fiscal_period_id from journal_entry where entry_type='payment' order by created_at"):
    fp = c.execute("select period_month from fiscal_period where id=?", (e[3],)).fetchone()[0]
    ls = [f"{a} D{d:.2f} H{h:.2f}" + (f" ME{(dm or 0) or (hm or 0):.2f}" if cm else "") for a, d, h, dm, hm, cm in c.execute("select a.account_code, l.debit_amount, l.credit_amount, l.debit_amount_me, l.credit_amount_me, l.currency_me from journal_entry_line l join chart_of_account a on a.id=l.chart_account_id where l.entry_id=?", (e[0],))]
    print(e[1], f"periodo {fp}", e[2], ls)
print('banco', [(n, t, a) for n, t, a in c.execute("select b.account_number, t.transaction_type, t.amount from bank_transaction t join bank_account b on b.id=t.account_id order by t.created_at")])
