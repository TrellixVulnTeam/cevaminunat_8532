import matplotlib.pyplot as plt
import numpy as np
import os

from losses import wasserstein_loss, perceptual_loss, SSIM, PSNR
from model import generator, discriminator, generator_and_discriminator
from keras.optimizers import Adam
from keras.preprocessing.image import img_to_array, load_img
from PIL import Image
from numpy import *

train_blurred_path = "/data/blurred_sharp/blurred/"
train_sharp_path = "/data/blurred_sharp/sharp/"

epochs = 10
batch_size = 4


def load_data():
    blurred_images = []
    sharp_images = []

    if os.path.exists(train_blurred_path) and os.path.exists(train_sharp_path):

        image_list = sorted(os.listdir(train_blurred_path))[:100]
        blurred_images = np.asarray(
            [(img_to_array(load_img(train_blurred_path + image).resize((256, 256), Image.ANTIALIAS)) - 128) / 128
             for image in image_list])

        image_list = sorted(os.listdir(train_sharp_path))[:100]
        sharp_images = np.asarray(
            [(img_to_array(load_img(train_sharp_path + image).resize((256, 256), Image.ANTIALIAS)) - 128) / 128 for
             image in image_list])

    else:
        print("You gave a invalid train path!")

    return blurred_images, sharp_images


def save_weights(gan):
    path = os.path.join("/data/weights")
    if not os.path.exists(path):
        os.makedirs(path)
    gan.save_weights(os.path.join(path, 'gan.h5'), True)


def train():
    print("Starting training")
    os.system("nvidia-smi")
    print('Epochs: {}'.format(epochs))
    print('Batch size: {}'.format(batch_size))

    blurred, sharp = load_data()
    opt = Adam(lr=1E-4, beta_1=0.9, beta_2=0.999, epsilon=1e-08)
    loss = [perceptual_loss, wasserstein_loss]
    metrics = [PSNR]
    true_batch = np.ones((batch_size, 1))
    false_batch = np.zeros((batch_size, 1))
    best_loss = 100000

    generator_model = generator()
    discriminator_model = discriminator()
    gan = generator_and_discriminator(generator_model, discriminator_model)

    discriminator_model.trainable = True
    discriminator_model.compile(optimizer=opt, loss=wasserstein_loss)
    discriminator_model.trainable = False

    gan.compile(optimizer=opt, loss=loss, loss_weights=[100, 1], metrics=metrics)
    discriminator_model.trainable = True

    print("Generator summary:")
    discriminator_model.summary()
    print("Discriminator summary:")
    discriminator_model.summary()
    print("GAN summary:")
    gan.summary()

    for epoch in range(epochs):
        print('Epoch: {}/{}'.format(epoch, epochs))
        print('Batches: {}'.format(blurred.shape[0] / batch_size))

        permutated_indexes = np.random.permutation(blurred.shape[0])

        discriminator_losses = []
        # discriminator_accuracies = []
        gan_losses = []
        gan_accuracies = []

        for batch in range(int(blurred.shape[0] / batch_size)):
            batch_indexes = permutated_indexes[batch * batch_size:(batch + 1) * batch_size]
            image_blur_batch = blurred[batch_indexes]
            image_full_batch = sharp[batch_indexes]

            # print(image_blur_batch.shape())
            # print(image_full_batch.shape())

            for _ in range(5):
                generated_images = generator_model.predict(x=image_blur_batch, batch_size=batch_size)
                discriminator_loss_real = discriminator_model.train_on_batch(image_full_batch, true_batch)
                discriminator_loss_fake = discriminator_model.train_on_batch(generated_images, false_batch)

                mean_discriminator_loss = np.add(discriminator_loss_fake, discriminator_loss_real) / 2
                # mean_discriminator_acc = np.add(discriminator_acc_fake, discriminator_acc_real) / 2

                discriminator_losses.append(mean_discriminator_loss)
                # discriminator_accuracies.append(mean_discriminator_acc)

            print('Batch {} discriminator loss : {}'.format(batch + 1, np.mean(discriminator_losses)))
            # print('Batch {} discriminator acc : {}'.format(batch + 1, np.mean(discriminator_accuracies)))

            discriminator_model.trainable = False

            gan_out = gan.train_on_batch(image_blur_batch, [image_full_batch, true_batch])
            gan_loss = gan_out[0]
            gan_acc = gan_out[1]

            gan_losses.append(gan_loss)
            gan_accuracies.append(gan_acc)
            print('Batch {} discriminator - generator loss : {}'.format(batch + 1, gan_out))
            print('Batch {} discriminator - generator acc : {}'.format(batch + 1, gan_acc))

            discriminator_model.trainable = True

        if gan_loss < best_loss:
            save_weights(gan)


if __name__ == '__main__':
    train()
