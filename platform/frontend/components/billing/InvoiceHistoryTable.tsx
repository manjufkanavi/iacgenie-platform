import React, { useState } from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import Badge from '../ui/Badge';

export interface Invoice {
  id: string;
  date: string;
  amount: number;
  status: string;
  description: string;
}

interface InvoiceHistoryTableProps {
  invoices: Invoice[];
  onDownload: (invoiceId: string) => void;
}

const InvoiceHistoryTable: React.FC<InvoiceHistoryTableProps> = ({ invoices, onDownload }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const filteredInvoices = invoices.filter((inv) => {
    const matchesSearch =
      inv.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inv.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inv.date.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus =
      statusFilter === 'all' || inv.status.toLowerCase() === statusFilter.toLowerCase();

    return matchesSearch && matchesStatus;
  });

  return (
    <Card padding="none" data-testid="invoice-history-card">
      <div className="p-6 border-b border-gray-150 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900">Invoice History</h2>
          <p className="text-sm text-gray-500 mt-0.5 font-medium">Download billing receipts and statements</p>
        </div>

        {/* Search & Filter Controls */}
        <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
          {/* Search bar */}
          <div className="relative flex-1 sm:w-64">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              type="text"
              placeholder="Search invoices..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="block w-full pl-9 pr-4 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-4 focus:ring-orange-100 focus:border-orange-500 transition-all duration-200 text-gray-900"
              data-testid="invoice-search-input"
            />
          </div>

          {/* Status selector */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="block px-3 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-4 focus:ring-orange-100 focus:border-orange-500 transition-all duration-200 bg-white text-gray-700 font-semibold"
            data-testid="invoice-status-filter"
          >
            <option value="all">All Statuses</option>
            <option value="paid">Paid</option>
            <option value="unpaid">Unpaid</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      {filteredInvoices.length === 0 ? (
        <div className="text-center p-16" data-testid="invoice-empty-state">
          <div className="mx-auto h-12 w-12 text-gray-400">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect width="20" height="14" x="2" y="5" rx="2" />
              <line x1="2" x2="22" y1="10" y2="10" />
            </svg>
          </div>
          <h3 className="mt-4 text-sm font-bold text-gray-900">No invoices found</h3>
          <p className="mt-2 text-sm text-gray-500 font-medium">Try adjusting your search filters or check back later.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-150" data-testid="invoice-table">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-6 py-3.5 text-left text-xs font-bold text-gray-400 uppercase tracking-wider">Date</th>
                <th scope="col" className="px-6 py-3.5 text-left text-xs font-bold text-gray-400 uppercase tracking-wider">Description</th>
                <th scope="col" className="px-6 py-3.5 text-left text-xs font-bold text-gray-400 uppercase tracking-wider">Amount</th>
                <th scope="col" className="px-6 py-3.5 text-left text-xs font-bold text-gray-400 uppercase tracking-wider">Status</th>
                <th scope="col" className="relative px-6 py-3.5"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {filteredInvoices.map((invoice) => (
                <tr key={invoice.id} data-testid={`invoice-row-${invoice.id}`}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-gray-900">{invoice.date}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 font-medium">{invoice.description}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 font-semibold">{'$' + invoice.amount.toFixed(2)}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Badge variant={invoice.status.toLowerCase() === 'paid' ? 'success' : 'danger'}>
                      {invoice.status}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => onDownload(invoice.id)}
                      data-testid={`invoice-download-button-${invoice.id}`}
                      className="hover:text-orange-500"
                    >
                      Download PDF
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
};

export default InvoiceHistoryTable;
