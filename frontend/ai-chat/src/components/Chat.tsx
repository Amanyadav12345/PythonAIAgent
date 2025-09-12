import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { chatAPI } from '../services/api';
import { ChatResponse, PartnerButton, ActionButton, ButtonData, CompanyButton, AddressButton } from '../types/api';
import './Chat.css';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'ai';
  timestamp: Date;
  sources?: string[];
  tools_used?: string[];
  button_data?: ButtonData;
  partner_buttons?: PartnerButton[];
  action_buttons?: ActionButton[];
  company_buttons?: CompanyButton[];
  address_buttons?: AddressButton[];
  requires_user_input?: boolean;
  input_type?: 'consignor_selection' | 'company_selection' | 'address_selection';
  selection_context?: {
    selected_partner?: any;
    selected_company?: any;
    companies_data?: any[];
  };
}

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { user, logout } = useAuth();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputText,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      const response: ChatResponse = await chatAPI.sendMessage(inputText);
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response.response,
        sender: 'ai',
        timestamp: new Date(),
        sources: response.sources,
        tools_used: response.tools_used,
        button_data: response.button_data,
        partner_buttons: response.partner_buttons,
        action_buttons: response.action_buttons,
        requires_user_input: response.requires_user_input,
        input_type: response.input_type,
      };

      setMessages(prev => [...prev, aiMessage]);
    } catch (error: any) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: 'Sorry, I encountered an error. Please try again.',
        sender: 'ai',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
  };

  const handleButtonClick = async (button: PartnerButton | ActionButton | CompanyButton | AddressButton, messageId: string) => {
    if (isLoading) return;

    // Create a user message showing what was selected
    const userMessage: Message = {
      id: Date.now().toString(),
      text: `Selected: ${button.text}`,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Handle partner button click
      const partnerButton = button as PartnerButton;
      if (partnerButton.partner_data && partnerButton.partner_data.id) {
        await handlePartnerSelection(partnerButton);
        return;
      }

      // Handle company button click
      const companyButton = button as CompanyButton;
      if (companyButton.company_data && companyButton.company_data.id) {
        await handleCompanySelection(companyButton, messageId);
        return;
      }

      // Handle address button click
      const addressButton = button as AddressButton;
      if (addressButton.address_data && addressButton.address_data.id) {
        await handleAddressSelection(addressButton);
        return;
      }

      // Handle action buttons (Show More, Skip, etc.)
      await handleActionButtonClick(button);

    } catch (error: any) {
      console.error('Button click error:', error);
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: `Sorry, I encountered an error processing your selection: ${error.message || 'Unknown error'}. Please try again.`,
        sender: 'ai',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePartnerSelection = async (partnerButton: PartnerButton) => {
    console.log('🔍 Calling getUserCompanies API for partner:', partnerButton.partner_data!.id);
    
    const companiesResponse = await chatAPI.getUserCompanies(partnerButton.partner_data!.id);
    console.log('📊 Companies response:', companiesResponse);

    const companies = companiesResponse?._items || [];
    
    if (companies.length === 0) {
      // No companies found
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: `✅ **Partner Selected: ${partnerButton.text}**\n\n⚠️ No companies found for this partner.\n\n✅ Partner selection completed successfully!`,
        sender: 'ai',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiMessage]);
    } else if (companies.length === 1) {
      // Single company - show addresses for selection
      await showAddressSelection(partnerButton, companies[0]);
    } else {
      // Multiple companies - show company selection
      showCompanySelection(partnerButton, companies);
    }
  };

  const showCompanySelection = (partnerButton: PartnerButton, companies: any[]) => {
    let companiesText = `✅ **Partner Selected: ${partnerButton.text}**\n\n`;
    companiesText += `**Select a Company (${companies.length} available):**\n\n`;

    // Create company buttons
    const companyButtons: CompanyButton[] = companies.map((company: any, index: number) => {
      const gst = company.identities?.find((id: any) => id.id_name === 'GST');
      const location = company.operation_locations?.[0];
      
      return {
        text: company.name || 'Unknown Company',
        value: company.name || 'Unknown Company',
        style: 'primary' as const,
        subtitle: `🏢 ${company.company_functions || ''} ${gst ? `• 🧾 ${gst.number}` : ''}`,
        company_data: {
          id: company._id,
          name: company.name,
          gst: gst?.number,
          city: location?.city?.name
        }
      };
    });

    const aiMessage: Message = {
      id: (Date.now() + 1).toString(),
      text: companiesText,
      sender: 'ai',
      timestamp: new Date(),
      company_buttons: companyButtons,
      requires_user_input: true,
      input_type: 'company_selection',
      selection_context: {
        selected_partner: partnerButton.partner_data,
        companies_data: companies
      }
    };

    setMessages(prev => [...prev, aiMessage]);
  };

  const handleCompanySelection = async (companyButton: CompanyButton, messageId: string) => {
    // Find the message with selection context to get companies data
    const contextMessage = messages.find(msg => msg.id === messageId);
    const companiesData = contextMessage?.selection_context?.companies_data || [];
    const selectedCompany = companiesData.find(company => company._id === companyButton.company_data!.id);
    
    if (selectedCompany) {
      await showAddressSelection(
        { partner_data: contextMessage?.selection_context?.selected_partner } as PartnerButton,
        selectedCompany
      );
    }
  };

  const showAddressSelection = async (partnerButton: PartnerButton, company: any) => {
    const addresses = company.operation_locations || [];
    
    let addressText = `✅ **Company Selected: ${company.name}**\n\n`;
    
    if (addresses.length === 0) {
      addressText += `⚠️ No addresses found for this company.\n\n✅ Selection completed successfully!`;
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: addressText,
        sender: 'ai',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiMessage]);
    } else if (addresses.length === 1) {
      // Single address - auto-select and complete
      const address = addresses[0];
      addressText += `**Selected Address:**\n`;
      addressText += `📍 ${address.city?.name || 'Unknown City'}\n`;
      addressText += `🏠 ${address.address_line_1 || 'Address not available'}\n`;
      if (address.pin) addressText += `📮 ${address.pin}\n`;
      addressText += `\n🎉 **Selection Complete!** Partner: ${partnerButton.partner_data?.name}, Company: ${company.name}`;

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: addressText,
        sender: 'ai',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiMessage]);
    } else {
      // Multiple addresses - show address selection
      addressText += `**Select an Address (${addresses.length} available):**\n\n`;

      const addressButtons: AddressButton[] = addresses.map((address: any, index: number) => ({
        text: `${address.location_purpose || 'Address'} - ${address.city?.name || 'Unknown City'}`,
        value: `${address.location_purpose || 'Address'} - ${address.city?.name || 'Unknown City'}`,
        style: 'primary' as const,
        subtitle: `🏠 ${address.address_line_1 || 'Address details'} ${address.pin ? `• 📮 ${address.pin}` : ''}`,
        address_data: {
          id: address._id,
          address_line_1: address.address_line_1,
          city: address.city?.name || 'Unknown City',
          pin: address.pin,
          location_type: address.location_purpose
        }
      }));

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: addressText,
        sender: 'ai',
        timestamp: new Date(),
        address_buttons: addressButtons,
        requires_user_input: true,
        input_type: 'address_selection',
        selection_context: {
          selected_partner: partnerButton.partner_data,
          selected_company: company
        }
      };

      setMessages(prev => [...prev, aiMessage]);
    }
  };

  const handleAddressSelection = async (addressButton: AddressButton) => {
    let completionText = `✅ **Address Selected: ${addressButton.text}**\n\n`;
    completionText += `**Final Selection Summary:**\n`;
    completionText += `👤 **Partner:** Selected partner\n`;
    completionText += `🏢 **Company:** Selected company\n`;
    completionText += `📍 **Address:** ${addressButton.address_data?.address_line_1}\n`;
    completionText += `🏙️ **City:** ${addressButton.address_data?.city}\n`;
    if (addressButton.address_data?.pin) {
      completionText += `📮 **PIN:** ${addressButton.address_data.pin}\n`;
    }
    completionText += `\n🎉 **Consignee selection completed successfully!**`;

    const aiMessage: Message = {
      id: (Date.now() + 1).toString(),
      text: completionText,
      sender: 'ai',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, aiMessage]);
  };

  const handleActionButtonClick = async (button: PartnerButton | ActionButton) => {
    const response: ChatResponse = await chatAPI.sendMessage(button.value);
    
    const aiMessage: Message = {
      id: (Date.now() + 1).toString(),
      text: response.response,
      sender: 'ai',
      timestamp: new Date(),
      sources: response.sources,
      tools_used: response.tools_used,
      button_data: response.button_data,
      partner_buttons: response.partner_buttons,
      action_buttons: response.action_buttons,
      requires_user_input: response.requires_user_input,
      input_type: response.input_type,
    };

    setMessages(prev => [...prev, aiMessage]);
  };

  return (
    <div className="chat-container">
      <header className="chat-header">
        <div className="header-left">
          <h1>🚛 Truck & Rolling Radius Assistant</h1>
          <span className="user-info">Welcome, {user?.full_name || user?.username}</span>
        </div>
        <div className="header-actions">
          <button onClick={clearChat} className="clear-button">
            Clear Chat
          </button>
          <button onClick={logout} className="logout-button">
            Logout
          </button>
        </div>
      </header>

      <div className="messages-container">
        {messages.length === 0 && (
          <div className="welcome-message">
            <h2>🚛 Welcome to Truck & Rolling Radius Management!</h2>
            <p>I can help you manage parcels, trips, vehicle routing, and rolling radius calculations for truck operations.</p>
            <p>Try asking me something like:</p>
            <ul>
              <li>"Create a parcel from Jaipur to Kolkata with 25 tonnes of steel"</li>
              <li>"Find available trucks for Delhi to Mumbai route"</li>
              <li>"Calculate rolling radius for tire size 295/80R22.5"</li>
              <li>"Search for materials suitable for heavy transport"</li>
              <li>"Check trip status and route optimization"</li>
            </ul>
          </div>
        )}
        
        {messages.map((message) => (
          <div
            key={message.id}
            className={`message ${message.sender === 'user' ? 'user-message' : 'ai-message'}`}
          >
            <div className="message-content">
              <div className="message-text">{message.text}</div>
              {message.sources && message.sources.length > 0 && (
                <div className="message-sources">
                  <strong>Sources:</strong>
                  <ul>
                    {message.sources.map((source, index) => (
                      <li key={index}>
                        <a href={source} target="_blank" rel="noopener noreferrer">
                          {source}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {message.tools_used && message.tools_used.length > 0 && (
                <div className="message-tools">
                  <strong>Tools used:</strong> {message.tools_used.join(', ')}
                </div>
              )}
              {message.button_data && (
                <div className="message-buttons">
                  <div className="partner-buttons">
                    {message.button_data.buttons.map((button, index) => (
                      <button
                        key={index}
                        className={`partner-button ${button.style}`}
                        onClick={() => handleButtonClick(button, message.id)}
                        disabled={isLoading}
                      >
                        <span className="button-text">{button.text}</span>
                        {button.subtitle && (
                          <span className="button-subtitle">{button.subtitle}</span>
                        )}
                      </button>
                    ))}
                  </div>
                  {message.button_data.action_buttons.length > 0 && (
                    <div className="action-buttons">
                      {message.button_data.action_buttons.map((button, index) => (
                        <button
                          key={index}
                          className={`action-button ${button.style}`}
                          onClick={() => handleButtonClick(button, message.id)}
                          disabled={isLoading}
                        >
                          {button.text}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
              {(message.partner_buttons || message.action_buttons || message.company_buttons || message.address_buttons) && (
                <div className="message-buttons">
                  {message.partner_buttons && (
                    <div className="partner-buttons">
                      {message.partner_buttons.map((button, index) => (
                        <button
                          key={index}
                          className={`partner-button ${button.style}`}
                          onClick={() => handleButtonClick(button, message.id)}
                          disabled={isLoading}
                        >
                          <span className="button-text">{button.text}</span>
                          {button.subtitle && (
                            <span className="button-subtitle">{button.subtitle}</span>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                  {message.company_buttons && (
                    <div className="company-buttons">
                      {message.company_buttons.map((button, index) => (
                        <button
                          key={index}
                          className={`partner-button ${button.style}`}
                          onClick={() => handleButtonClick(button, message.id)}
                          disabled={isLoading}
                        >
                          <span className="button-text">{button.text}</span>
                          {button.subtitle && (
                            <span className="button-subtitle">{button.subtitle}</span>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                  {message.address_buttons && (
                    <div className="address-buttons">
                      {message.address_buttons.map((button, index) => (
                        <button
                          key={index}
                          className={`partner-button ${button.style}`}
                          onClick={() => handleButtonClick(button, message.id)}
                          disabled={isLoading}
                        >
                          <span className="button-text">{button.text}</span>
                          {button.subtitle && (
                            <span className="button-subtitle">{button.subtitle}</span>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                  {message.action_buttons && (
                    <div className="action-buttons">
                      {message.action_buttons.map((button, index) => (
                        <button
                          key={index}
                          className={`action-button ${button.style}`}
                          onClick={() => handleButtonClick(button, message.id)}
                          disabled={isLoading}
                        >
                          {button.text}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="message-timestamp">
              {message.timestamp.toLocaleTimeString()}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="message ai-message">
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={sendMessage} className="input-form">
        <div className="input-container">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Ask about trucks, parcels, routes, or rolling radius calculations..."
            disabled={isLoading}
            className="message-input"
          />
          <button
            type="submit"
            disabled={isLoading || !inputText.trim()}
            className="send-button"
          >
            {isLoading ? '⏳' : '🚀'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default Chat;