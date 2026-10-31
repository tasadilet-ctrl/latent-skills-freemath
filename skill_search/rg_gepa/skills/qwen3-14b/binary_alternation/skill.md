To solve the task, follow these steps:

1. **Understand the Alternating Pattern**: An alternating binary string alternates between '0' and '1'. There are two valid patterns: one starting with '0' (e.g., "0101...") and one starting with '1' (e.g., "1010...").

2. **Check Feasibility**: Count the number of '0's and '1's in the string. If the absolute difference between the counts is greater than 1, it is impossible to form an alternating string, and the answer is -1.

3. **Define Target Patterns**: Based on the string length, determine the two possible target patterns (starting with '0' or '1'). For each pattern, compare it with the original string and count how many positions do not match.

4. **Count Mismatches**: For each target pattern, count how many positions have a '0' where a '1' is needed and vice versa. These mismatches must be resolved by swaps.

5. **Calculate Swaps**: Each swap can fix two mismatches (a '0' in a '1' position and a '1' in a '0' position). Divide the total number of mismatches by 2 to get the minimum number of swaps required for each pattern. If the number of mismatches is odd, the pattern is not feasible.

6. **Choose the Minimum**: Compare the swap counts for both patterns. If both patterns are feasible, choose the smaller one as the result. If only one is feasible, choose that one. If neither is feasible, return -1.

7. **Verify and Finalize**: Ensure that the chosen solution meets the alternating condition and that the counts of '0's and '1's are compatible with the pattern. Provide the final answer.