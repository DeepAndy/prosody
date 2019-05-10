import torch
from torch import nn
from pytorch_pretrained_bert import BertModel


class Net(nn.Module):
    def __init__(self, device, vocab_size=None):
        super().__init__()
        self.bert = BertModel.from_pretrained('bert-base-uncased')

        self.fc = nn.Linear(768, vocab_size)
        self.device = device

    def forward(self, x, y):

        x = x.to(self.device)
        y = y.to(self.device)

        if self.training:
            self.bert.train()
            encoded_layers, _ = self.bert(x)
            enc = encoded_layers[-1]
        else:
            self.bert.eval()
            with torch.no_grad():
                encoded_layers, _ = self.bert(x)
                enc = encoded_layers[-1]

        logits = self.fc(enc)
        y_hat = logits.argmax(-1)
        return logits, y, y_hat
