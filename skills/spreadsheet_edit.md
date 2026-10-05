# Locate the Range, Compute in Python, Write Values

1. **Resolve the target before writing anything.** Convert the answer range to
   explicit first and last row and column numbers, and name the worksheet by
   the exact string given. openpyxl is 1-indexed and its `cell(row, column)`
   takes row first; an off-by-one here silently writes a correct answer into
   the wrong cells.

2. **Find the header row and the first data row separately.** Do not assume row
   1 is data or that row 1 is a header. Read a few rows and decide from their
   contents, then record the data range as explicit bounds.

3. **Read the inputs into plain Python structures first.** Pull the values you
   need into lists or dicts, and do the filtering, matching, sorting and
   arithmetic there. Do not attempt the transformation cell by cell in place.

4. **Write computed values, never formulas.** A formula written by openpyxl is
   stored without a cached result, so it reads back as empty. Evaluate in
   Python and write the resulting number or string.

5. **Preserve types.** A quantity that is numeric in the source stays numeric in
   the answer: do not write `"12"` where `12` is meant, do not round unless the
   task says to, and keep dates as dates rather than their string rendering.

6. **Stay inside the answer range.** Write every cell the range covers and none
   outside it. Where the task gives a worked example in part of the range,
   match its layout exactly for the parts you fill in.

7. **Re-read before saving.** Load the cells you wrote back and check the count,
   the bounds and a sample of values against what the task asked for.
