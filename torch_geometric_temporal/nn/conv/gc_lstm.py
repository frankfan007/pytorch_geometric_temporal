import torch
from torch.nn import Parameter
from torch_geometric.nn import ChebConv
from torch_geometric.nn.inits import glorot, zeros


class GCLSTM(torch.nn.Module):
    r"""An implementation of the the Integrated Graph Convolutional Long Short Term
    Memory Cell. For details see this paper: `"GC-LSTM: Graph Convolution Embedded LSTM
    for Dynamic Link Prediction." <https://arxiv.org/abs/1812.04206>`_

    Args:
        in_channels (int): Number of input features.
        out_channels (int): Number of output features.
        K (int): Chebyshev filter size.
    """
    def __init__(self, in_channels: int, out_channels: int, K: int):
        super(GCLSTM, self).__init__()

        self.in_channels = in_channels
        self.out_channels = out_channels
        self.K = K
        self._create_parameters_and_layers()
        self._set_parameters()


    def _create_input_gate_parameters_and_layers(self):

        self.conv_i = ChebConv(in_channels=self.out_channels,
                               out_channels=self.out_channels,
                               K=self.K)

        self.W_i = Parameter(torch.Tensor(self.in_channels, self.out_channels))
        self.b_i = Parameter(torch.Tensor(1, self.out_channels))


    def _create_forget_gate_parameters_and_layers(self):

        self.conv_f = ChebConv(in_channels=self.out_channels,
                               out_channels=self.out_channels,
                               K=self.K)

        self.W_f = Parameter(torch.Tensor(self.in_channels, self.out_channels))
        self.b_f = Parameter(torch.Tensor(1, self.out_channels))


    def _create_cell_state_parameters_and_layers(self):

        self.conv_c = ChebConv(in_channels=self.out_channels,
                               out_channels=self.out_channels,
                               K=self.K)

        self.W_c = Parameter(torch.Tensor(self.in_channels, self.out_channels))
        self.b_c = Parameter(torch.Tensor(1, self.out_channels))


    def _create_output_gate_parameters_and_layers(self):

        self.conv_o = ChebConv(in_channels=self.out_channels,
                               out_channels=self.out_channels,
                               K=self.K)

        self.W_o = Parameter(torch.Tensor(self.in_channels, self.out_channels))
        self.b_o = Parameter(torch.Tensor(1, self.out_channels))


    def _create_parameters_and_layers(self):
        self._create_input_gate_parameters_and_layers()
        self._create_forget_gate_parameters_and_layers()
        self._create_cell_state_parameters_and_layers()
        self._create_output_gate_parameters_and_layers()


    def _set_parameters(self):
        glorot(self.W_i)
        glorot(self.W_f)
        glorot(self.W_c)
        glorot(self.W_o)
        zeros(self.b_i)
        zeros(self.b_f)
        zeros(self.b_c)
        zeros(self.b_o)


    def _set_hidden_state(self, X, H):
        if H is None:
            H = torch.zeros(X.shape[0], self.out_channels)
        return H


    def _set_cell_state(self, X, C):
        if C is None:
            C = torch.zeros(X.shape[0], self.out_channels)
        return C


    def _calculate_input_gate(self, X, edge_index, edge_weight, H, C):
        I = torch.matmul(X, self.W_i)
        I = I + self.conv_i(H, edge_index, edge_weight)
        I = I + self.b_i
        I = torch.sigmoid(I)
        return I


    def _calculate_forget_gate(self, X, edge_index, edge_weight, H, C):
        F = torch.matmul(X, self.W_f)
        F = F + self.conv_f(H, edge_index, edge_weight)
        F = F + self.b_f
        F = torch.sigmoid(F)
        return F


    def _calculate_cell_state(self, X, edge_index, edge_weight, H, C, I, F):
        T = torch.matmul(X, self.W_c)
        T = T + self.conv_c(H, edge_index, edge_weight)
        T = T + self.b_c
        T = torch.tanh(T)
        C = F*C + I*T
        return C

    def _calculate_output_gate(self, X, edge_index, edge_weight, H, C):
        O = torch.matmul(X, self.W_o)
        O = O + self.conv_o(H, edge_index, edge_weight)
        O = O + self.b_o
        O = torch.sigmoid(O)
        return O


    def _calculate_hidden_state(self, O, C):
        H = O * torch.tanh(C)
        return H


    def forward(self, X: torch.FloatTensor, edge_index: torch.LongTensor,
                edge_weight: torch.FloatTensor=None, H: torch.FloatTensor=None, C: torch.FloatTensor=None):
        """
        Making a forward pass. If edge weights are not present the forward pass
        defaults to an unweighted graph. If the hidden state and cell state
        matrices are not present when the forward pass is called these are
        initialized with zeros.

        Arg types:
            * **X** *(PyTorch Float Tensor)* - Node features.
            * **edge_index** *(PyTorch Long Tensor)* - Graph edge indices.
            * **edge_weight** *(PyTorch Long Tensor)* - Edge weight vector (optional).
            * **H** *(PyTorch Float Tensor)* - Hidden state matrix for all nodes (optional).
            * **C** *(PyTorch Float Tensor)* - Cell state matrix for all nodes (optional).

        Return types:
            * **H** *(PyTorch Float Tensor)* - Hidden state matrix for all nodes.
            * **C** *(PyTorch Float Tensor)* - Cell state matrix for all nodes.
        """
        H = self._set_hidden_state(X, H)
        C = self._set_cell_state(X, C)
        I = self._calculate_input_gate(X, edge_index, edge_weight, H, C)
        F = self._calculate_forget_gate(X, edge_index, edge_weight, H, C)
        C = self._calculate_cell_state(X, edge_index, edge_weight, H, C, I, F)
        O = self._calculate_output_gate(X, edge_index, edge_weight, H, C)
        H = self._calculate_hidden_state(O, C)
        return H, C
