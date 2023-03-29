# -*- coding: utf-8 -*-
"""PFE.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1uL3gpwugF49KvHekwuei7wtJ1XBL0j0E

# Normalizing flow | 1D using CDF
"""

import torch
import torch.utils.data as data 
import torch.nn as nn
import numpy as np
import matplotlib.pyplot as plt
from torch import distributions
import torch.distributions as D

from torch.distributions.uniform import Uniform
from torch.distributions import Normal
import torch.distributions.transforms as transform

import torch.optim as optim

"""Données

On apprend la mixture des gaussiens grâce aux échantillons de la fonction generate_mixture_of_gaussians
"""

def generate_mixture_of_gaussians(num_of_points):
    n = num_of_points // 5
    gaussian1 = np.random.normal(loc=-1, scale=0.25, size=(n,))
    gaussian2 = np.random.normal(loc=0.5, scale=0.25, size=(n,))
    gaussian3 = np.random.normal(loc=0.25, scale=0.35, size=(n,))
    gaussian4 = np.random.normal(loc=-0.5, scale=0.05, size=(n,))
    gaussian5 = np.random.normal(loc=0, scale=0.15, size=(n,))
    return np.concatenate([gaussian1, gaussian2, gaussian3, gaussian4, gaussian5])

class NumpyDataset(data.Dataset):
    def __init__(self, array):
        super().__init__()
        self.array = array

    def __len__(self):
        return len(self.array)

    def __getitem__(self, index):
        return self.array[index]

n_train, n_test = 10000, 1000
train_data = generate_mixture_of_gaussians(n_train)
test_data = generate_mixture_of_gaussians(n_test)

train_loader = data.DataLoader(NumpyDataset(train_data), batch_size=128, shuffle=True)
test_loader = data.DataLoader(NumpyDataset(test_data), batch_size=128, shuffle=True)
#for x in train_loader:
  #plt.hist(x, bins=100)
plt.hist(train_data, bins=100)
#plt.hist(test_data, bins=100)

"""Modèle"""

class Flow1d(nn.Module):
    def __init__(self, n_components):
        super(Flow1d, self).__init__()
        self.mu = nn.Parameter(torch.randn(n_components), requires_grad=True)
        self.sigma = nn.Parameter(torch.ones(n_components), requires_grad=True)
        self.weight = nn.Parameter(torch.ones(n_components), requires_grad=True)

    #Model prediction
    def forward(self, x):
        x = x.view(-1,1)
        weights = self.weight.softmax(dim=0).view(1,-1) #Somme=1
        distribution = Normal(self.mu, self.sigma)
        z = (distribution.cdf(x) * weights).sum(dim=1)
        dz_by_dx = (distribution.log_prob(x).exp() * weights).sum(dim=1)
        return z, dz_by_dx
  
def loss_function(target_distribution, z, dz_by_dx):
    log_likelihood = target_distribution.log_prob(z) + dz_by_dx.log()
    return -log_likelihood.mean()

def train(model, train_loader, optimizer, target_distribution):
    model.train()
    for x in train_loader:
        z, dz_by_dx = model(x)
        loss = loss_function(target_distribution, z, dz_by_dx)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
def eval_loss(model, data_loader, target_distribution):
    model.eval()
    total_loss = 0
    for x in data_loader:
        z, dz_by_dx = model(x)
        loss = loss_function(target_distribution, z, dz_by_dx)
        total_loss += loss * x.size(0)
    return (total_loss / len(data_loader.dataset)).item()

def train_and_eval(epochs, lr, train_loader, test_loader, target_distribution):
    flow = Flow1d(n_components=5)
    optimizer = torch.optim.Adam(flow.parameters(), lr=lr)
    train_losses, test_losses = [], []
    for epoch in range(epochs):
        train(flow, train_loader, optimizer, target_distribution)
        train_losses.append(eval_loss(flow, train_loader, target_distribution))
        test_losses.append(eval_loss(flow, test_loader, target_distribution))
    return flow, train_losses, test_losses

"""Plot"""

target_distribution = Normal(0.0, 1.0)
flow, train_losses, test_losses = train_and_eval(50, 5e-3, train_loader, test_loader, target_distribution)

_ = plt.plot(train_losses, label='train_loss')
_ = plt.plot(test_losses, label='test_loss')
plt.legend()

x = np.linspace(-3,3,1000)
with torch.no_grad():
    z, dz_by_dx = flow(torch.FloatTensor(x))
    px = (target_distribution.log_prob(z) + dz_by_dx.log()).exp().cpu().numpy()
    
_, axes = plt.subplots(1,2, figsize=(12,4))
_ = axes[0].grid(), axes[1].grid()
_ = axes[0].plot(x,px)
_ = axes[0].set_title('Learned probability distribution')

_ = axes[1].plot(x,z)
_ = axes[1].set_title('x -> z')