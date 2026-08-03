import React, { useState } from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';

export interface PaymentMethod {
  id: string;
  brand: 'visa' | 'mastercard' | 'amex' | 'discover';
  last4: string;
  expMonth: number;
  expYear: number;
  isDefault: boolean;
}

const PaymentMethodsContainer: React.FC = () => {
  const [methods, setMethods] = useState<PaymentMethod[]>([
    { id: 'pm_1', brand: 'visa', last4: '4242', expMonth: 12, expYear: 2028, isDefault: true },
    { id: 'pm_2', brand: 'mastercard', last4: '5555', expMonth: 8, expYear: 2027, isDefault: false },
  ]);

  const [showAddForm, setShowAddForm] = useState(false);
  const [cardNumber, setCardNumber] = useState('');
  const [expiry, setExpiry] = useState('');
  const [cvc, setCvc] = useState('');

  const getBrandIcon = (brand: string) => {
    switch (brand) {
      case 'visa':
        return (
          <span className="font-extrabold text-blue-600 text-sm tracking-wider uppercase bg-blue-50 px-2.5 py-1 rounded border border-blue-200">
            Visa
          </span>
        );
      case 'mastercard':
        return (
          <span className="font-extrabold text-red-500 text-sm tracking-wider uppercase bg-red-50 px-2.5 py-1 rounded border border-red-200">
            MC
          </span>
        );
      default:
        return (
          <span className="font-extrabold text-gray-500 text-sm tracking-wider uppercase bg-gray-50 px-2.5 py-1 rounded border border-gray-200">
            Card
          </span>
        );
    }
  };

  const handleSetDefault = (id: string) => {
    setMethods((prev) =>
      prev.map((m) => ({
        ...m,
        isDefault: m.id === id,
      }))
    );
  };

  const handleDelete = (id: string) => {
    setMethods((prev) => prev.filter((m) => m.id !== id));
  };

  const handleAddCard = (e: React.FormEvent) => {
    e.preventDefault();
    if (!cardNumber || !expiry || !cvc) return;

    const last4 = cardNumber.replace(/\s/g, '').slice(-4) || '9999';
    const [month, year] = expiry.split('/');
    const expMonth = parseInt(month) || 12;
    const expYear = parseInt(year) || 2029;

    const newMethod: PaymentMethod = {
      id: `pm_${Date.now()}`,
      brand: cardNumber.startsWith('5') ? 'mastercard' : 'visa',
      last4,
      expMonth,
      expYear,
      isDefault: methods.length === 0,
    };

    setMethods((prev) => [...prev, newMethod]);
    setCardNumber('');
    setExpiry('');
    setCvc('');
    setShowAddForm(false);
  };

  return (
    <Card padding="none" data-testid="payment-methods-card">
      <div className="p-6 border-b border-gray-150 flex justify-between items-center">
        <div>
          <h2 className="text-lg font-bold text-gray-900">Payment Methods</h2>
          <p className="text-sm text-gray-500 mt-0.5">Manage credit cards used for subscription billing</p>
        </div>
        {!showAddForm && (
          <Button
            size="sm"
            variant="primary"
            onClick={() => setShowAddForm(true)}
            className="bg-gradient-to-r from-orange-500 to-red-500 border-0 font-bold"
            data-testid="add-payment-method-button"
          >
            Add Card
          </Button>
        )}
      </div>

      <div className="p-6">
        {showAddForm ? (
          <form onSubmit={handleAddCard} className="space-y-4" data-testid="add-card-form">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="sm:col-span-2">
                <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                  Card Number
                </label>
                <input
                  type="text"
                  required
                  placeholder="4242 4242 4242 4242"
                  value={cardNumber}
                  onChange={(e) => setCardNumber(e.target.value)}
                  className="block w-full px-4 py-3 border border-gray-200 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-4 focus:ring-orange-100 focus:border-orange-500 transition-all duration-200 text-gray-900"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                    Expiry
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="MM/YY"
                    value={expiry}
                    onChange={(e) => setExpiry(e.target.value)}
                    className="block w-full px-4 py-3 border border-gray-200 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-4 focus:ring-orange-100 focus:border-orange-500 transition-all duration-200 text-gray-900 text-center"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                    CVC
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="***"
                    value={cvc}
                    onChange={(e) => setCvc(e.target.value)}
                    className="block w-full px-4 py-3 border border-gray-200 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-4 focus:ring-orange-100 focus:border-orange-500 transition-all duration-200 text-gray-900 text-center"
                  />
                </div>
              </div>
            </div>

            <div className="flex space-x-3 pt-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowAddForm(false)}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                type="submit"
                className="bg-gradient-to-r from-orange-500 to-red-500 border-0 font-bold"
              >
                Save Payment Method
              </Button>
            </div>
          </form>
        ) : methods.length === 0 ? (
          <div className="text-center py-6">
            <p className="text-sm font-semibold text-gray-500">No payment methods added yet.</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100" data-testid="payment-methods-list">
            {methods.map((method) => (
              <div
                key={method.id}
                className="flex flex-col sm:flex-row justify-between items-start sm:items-center py-4 first:pt-0 last:pb-0 gap-4"
                data-testid={`payment-method-row-${method.id}`}
              >
                <div className="flex items-center space-x-4">
                  {getBrandIcon(method.brand)}
                  <div>
                    <p className="text-sm font-bold text-gray-900">
                      •••• •••• •••• {method.last4}
                      {method.isDefault && (
                        <span className="ml-2.5 inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-orange-50 text-orange-600 border border-orange-200">
                          Default
                        </span>
                      )}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      Expires {method.expMonth.toString().padStart(2, '0')}/{method.expYear}
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-3 w-full sm:w-auto justify-end">
                  {!method.isDefault && (
                    <button
                      type="button"
                      onClick={() => handleSetDefault(method.id)}
                      className="text-xs font-bold text-gray-500 hover:text-orange-500 transition-colors uppercase tracking-wider"
                      data-testid={`set-default-${method.id}`}
                    >
                      Make Default
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => handleDelete(method.id)}
                    className="text-xs font-bold text-red-500 hover:text-red-600 transition-colors uppercase tracking-wider"
                    data-testid={`delete-card-${method.id}`}
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
};

export default PaymentMethodsContainer;
