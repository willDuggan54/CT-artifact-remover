# CT-artifact-remover
Code from my 2021 Summer REU Project "Deep Learning for Sparse-View Filtered Backprojection Imaging".  
**Absract:**  
Filtered Backprojection (FBP) algorithms are computationally efficient and therefore, widely used. These algorithms however, require a lot of data to correctly compute an image through an inverse function. In the case of Computed Tomography (CT) scans, collecting a lot of data means taking lots of X-ray samples. These X-rays can be both expensive and have health effects on the patient. Sparse-view scans are undersampled, meaning they collect less data. This approach however, has the potential to introduce artifacts into the image. This project focuses on using Deep Learning techniques to remove these artifacts from the sparse-view filtered backprojection CT images.  
**About the Project:**  
This project investigated different Deep Learning architectures, loss functions, and training methods to compare which ones were able to produce the most realistic reconstructions of the undersampled images. Many of the failed architectures and techniques have been ommitted from this repository, and only the ones that produced viable or good results have been left in. The shortcomings of the ommitted models provided valuable insight as to what the well-performing models were doing correctly. The Convolutional Neural Network (CNN) FBPConvNet model was used as a benchmark to compare against the Generative Adversarial Network (GAN) models, Pix2pix and the Perceptual Adversarial Network (PAN).  
**Results:**  
Three different quantitative measurements were used: Mean Squared Error (MSE), Peak signal-to-noise ratio (PSNR), and Structure Similarity Index (SSIM). The training epochs that this score was achieved at is also denoted at the right.
The results showed better performance in the SSIM measure for both GAN architectures when compared to the CNN architecture. This is because of the stronger learning GANs can have, utilizing the second network to help the generator learn. Both GANs also have a more complex loss function when compared to the CNN, helping them to learn more features of the input image. Shown below is an example from the best performing network, Pix2pix using the ErrorCalculator.ipynb file:
![image](https://user-images.githubusercontent.com/71538648/137009652-599ba111-efb5-43c8-9994-de335b961f7f.png)  
**More Info about the Files (in case you want to run them):**  
All the models have their own main/runner functions already in their respective programs. This was done because each model has different batch sizes, methods, and, cross-validation steps.
