import React, { useState } from 'react';
import Card from './Card';
import { ICONS } from '.././constants';
import { AccordionItem } from './types';

interface AccordionProps {
    items: AccordionItem[];
}

const Accordion: React.FC<AccordionProps> = ({ items }) => {
    const [openId, setOpenId] = useState<string | null>(items.length > 0 ? items[0].id : null);

    const toggleItem = (id: string) => {
        setOpenId(prevId => (prevId === id ? null : id));
    };

    return (
        <div className="space-y-4">
            {items.map((item) => {
                const isOpen = openId === item.id;
                return (
                    <Card key={item.id} padding="none" className="overflow-hidden">
                        <button
                            onClick={() => toggleItem(item.id)}
                            className="w-full text-left flex items-center justify-between p-6 relative z-10"
                            aria-expanded={isOpen}
                        >
                            <div className="flex items-center relative z-10">
                                <div className="text-brand-primary w-6 h-6 relative z-10">{item.icon}</div>
                                <div className="ml-4">
                                    <h3 className="font-semibold text-gray-900">{item.title}</h3>
                                    <p className="text-sm text-gray-500">{item.subtitle}</p>
                                </div>
                            </div>
                            <span className={`transform transition-transform duration-200 text-gray-400 ${isOpen ? 'rotate-180' : ''}`}>
                                {ICONS.CHEVRON_DOWN}
                            </span>
                        </button>
                        <div
                            className={`transition-all duration-300 ease-in-out overflow-hidden ${isOpen ? 'max-h-[1000px]' : 'max-h-0'}`}
                        >
                            <div className="p-6 border-t border-gray-200 relative z-0">
                                {item.content}
                            </div>
                        </div>
                    </Card>
                );
            })}
        </div>
    );
};

export default Accordion;