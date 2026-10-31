To solve the task, follow these steps:

1. **Analyze the input matrix and parameters**: Determine the matrix dimensions (rows and columns), kernel size, and stride. When the stride equals the kernel size, pooling regions do not overlap.

2. **Calculate the output matrix size**: Use the formula `floor((input_size - kernel_size) / stride) + 1` for both rows and columns. If the result is less than 1 for any dimension, the operation cannot be performed.

3. **Identify valid pooling regions**: Starting from the top-left corner, slide the kernel across the matrix according to the stride. Ensure that the kernel stays fully within the matrix boundaries. If the kernel cannot fit in a dimension, skip that region.

4. **Compute the average for each valid region**: For each valid submatrix defined by the kernel, calculate the average of its elements. If the kernel size is 1, the output matrix matches the input matrix.

5. **Construct the output matrix**: Place each computed average in the output matrix in the same order as the regions were processed. Ensure the matrix has the correct dimensions and format.

6. **Verify correctness**: Check that all calculations are accurate, the output matrix size is correct, and no regions were missed or incorrectly included. Ensure all elements are formatted to 2 decimal places.

By systematically applying these steps, the model can perform average pooling on any matrix with the given kernel size and stride, ensuring accuracy and consistency across different inputs.