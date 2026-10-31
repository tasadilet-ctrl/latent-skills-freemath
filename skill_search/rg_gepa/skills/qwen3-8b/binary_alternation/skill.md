To determine the minimum number of swaps required to make a binary string alternating, follow this structured approach:

1. **Identify the Two Valid Patterns**: An alternating binary string must follow one of two patterns: starting with '0' (e.g., "0101...") or starting with '1' (e.g., "1010..."). These are the only two valid alternating patterns for any binary string.

2. **Check Feasibility for Each Pattern**: For each pattern, calculate the required number of '0's and '1's based on the string length. For a string of length `n`, the pattern starting with '0' requires `ceil(n/2)` zeros and `floor(n/2)` ones, while the pattern starting with '1' requires the opposite. If the string's actual counts of '0's and '1's do not match the required counts for either pattern, that pattern is not feasible.

3. **Count Mismatches for Feasible Patterns**: For each feasible pattern, compare the string to the pattern and count the number of positions where the characters do not match.

4. **Calculate Minimum Swaps**: Each swap can fix two mismatches. Therefore, the minimum number of swaps required is the number of mismatches divided by 2. If the number of mismatches is odd, one additional swap is needed to fix the last mismatch.

5. **Choose the Minimum Swaps**: If both patterns are feasible, choose the one requiring fewer swaps. If only one pattern is feasible, use its swap count. If neither is feasible, return -1.