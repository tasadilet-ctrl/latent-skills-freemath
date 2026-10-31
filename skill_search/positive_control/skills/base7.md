# Converting a number to base 7, written out

Do not convert in one step.

1. Divide the number by 7. Write the quotient and the remainder exactly, and check: quotient × 7 + remainder = the number you divided.
2. Repeat step 1 on the quotient, writing each division on its own line, until the quotient is 0.
3. The base-7 digits are the remainders, read from the last division back to the first.
4. Every digit must be between 0 and 6; if one is not, redo that division.
5. Check by converting back: multiply out the digits by powers of 7 (1, 7, 49, 343, 2401, 16807, ...) and confirm the sum equals the original number.
6. Give the base-7 numeral as a string of digits, with no subscript.
