# Day of the week for a Gregorian date, written out

Use Zeller's congruence; do not recall or guess the weekday.

1. Let q be the day of the month, m the month, Y the year. If the month is January or February, treat it as month 13 or 14 of the previous year (so m = 13 or 14 and Y = Y − 1).
2. Let K = Y mod 100 (year of the century) and J = floor(Y / 100) (century).
3. Compute each term separately and write it down: q; floor(13(m + 1) / 5); K; floor(K / 4); floor(J / 4); 5J.
4. Add the six terms and take the sum mod 7 to get h.
5. Map h to the weekday: 0 = Saturday, 1 = Sunday, 2 = Monday, 3 = Tuesday, 4 = Wednesday, 5 = Thursday, 6 = Friday.
6. Give the weekday as a single English word.
