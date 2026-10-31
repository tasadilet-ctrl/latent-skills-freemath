To solve the task, follow a systematic, layer-by-layer approach:

1. **Initialize boundaries**: Define `top`, `bottom`, `left`, and `right` to represent the current layer's boundaries. Start with `top = 0`, `bottom = rows - 1`, `left = 0`, `right = cols - 1`.

2. **Traverse the top row**: Move from `left` to `right`, adding each element to the result. After this, increment `top` to move inward.

3. **Traverse the right column**: Move from `top` to `bottom`, adding each element to the result. After this, decrement `right` to move inward.

4. **Traverse the bottom row (if applicable)**: If `top <= bottom`, move from `right` to `left`, adding each element to the result. After this, decrement `bottom` to move inward.

5. **Traverse the left column (if applicable)**: If `left <= right`, move from `bottom` to `top`, adding each element to the result. After this, increment `left` to move inward.

6. **Repeat steps 2–5** until all elements are visited. Stop when `top > bottom` or `left > right`.

7. **Check for completeness**: Ensure that the result contains exactly `rows * cols` elements. If not, retrace the steps to identify any missed elements or incorrect traversal.

8. **Verify correctness**: Review the traversal order and ensure that it adheres to the spiral pattern—clockwise, starting from the top-left corner and peeling layers inward.

By following this structured, repeatable method, the model can consistently generate the correct spiral order for any given matrix.