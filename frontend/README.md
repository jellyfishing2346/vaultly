# Vaultly Frontend

Next.js frontend for the Vaultly P2P payment system.

## Features

- **Authentication**: User signup and login with JWT tokens
- **Dashboard**: Real-time balance display and activity feed
- **Send Money**: Transfer money to other users with @username
- **Activity Feed**: View sent and received transfers
- **Responsive Design**: Mobile-friendly interface with Tailwind CSS
- **Error Handling**: User-friendly error messages and loading states
- **Empty States**: Helpful UI when no activity exists

## Tech Stack

- **Next.js 14**: React framework with App Router
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first CSS framework
- **React Context**: State management for authentication
- **Axios**: HTTP client for API communication

## Getting Started

### Prerequisites

- Node.js 18+ installed
- Backend API running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env.local

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:3000`

### Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Project Structure

```
src/
├── app/
│   ├── dashboard/page.tsx      # Main dashboard with balance and activity
│   ├── login/page.tsx          # Login form
│   ├── signup/page.tsx         # Signup form
│   ├── layout.tsx              # Root layout with AuthProvider
│   ├── page.tsx                # Landing page with routing
│   └── globals.css             # Global styles
├── contexts/
│   └── AuthContext.tsx         # Authentication state management
├── lib/
│   └── api.ts                  # API client with typed interfaces
└── components/                 # (Add reusable components here)
```

## API Integration

The frontend communicates with the backend via REST API:

- **Authentication**: `/auth/signup`, `/auth/login`
- **User Data**: `/me`
- **Transfers**: `/transfers`, `/transfers/activity`

All API calls include JWT tokens in the Authorization header after login.

## Development

### Build for Production

```bash
npm run build
npm start
```

### Linting

```bash
npm run lint
```

## Key Features Implementation

### Authentication Flow

1. User signs up/logs in via API
2. JWT token stored in localStorage
3. Token sent with all subsequent API requests
4. AuthContext manages authentication state globally
5. Protected routes redirect to login if not authenticated

### Send Money Flow

1. User enters recipient @username and amount
2. Client validates amount > 0 and sufficient balance
3. Generates unique idempotency key
4. Calls transfer API with idempotency header
5. Handles fraud detection (pending_review status)
6. Refreshes balance and activity on success

### Activity Feed

1. Fetches recent transfers from API
2. Displays sent/received status with color coding
3. Shows counterparty handle and note
4. Formats timestamps and amounts
5. Shows empty state when no activity exists

## Error Handling

- Network errors display user-friendly messages
- Validation errors show specific field issues
- Loading states for all async operations
- Graceful handling of API failures

## Mobile Responsiveness

- Responsive grid layouts
- Touch-friendly form inputs
- Optimized spacing for small screens
- Readable text sizes on mobile devices

## Future Enhancements

- Real-time updates via WebSockets
- Bill splitting feature
- Transaction details view
- Search/filter activity feed
- Profile management
- Notification system
