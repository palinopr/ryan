# Meta Ryan System Flow Diagram

## Main System Architecture Flow

```mermaid
graph TB
    %% Entry Points
    User[("👤 User<br/>(Phone/Message)")] 
    
    %% Security Layer
    Security["🔐 Security Agent<br/>─────────────<br/>• Phone Validation<br/>• Permission Check<br/>• Rate Limiting<br/>• Audit Logging"]
    
    %% Supervisor
    Supervisor["🎯 Supervisor Agent<br/>─────────────<br/>• Intent Analysis<br/>• Agent Routing<br/>• Response Aggregation"]
    
    %% Core Agents
    MetaAgent["📊 Meta Campaign Agent<br/>─────────────<br/>• Campaign Analysis<br/>• ROAS Calculation<br/>• City Performance<br/>• Dynamic SDK Queries"]
    
    GHLAgent["📱 GoHighLevel Agent<br/>─────────────<br/>• CRM Operations<br/>• Message Sending<br/>• Contact Management<br/>• MCP Tool Execution"]
    
    %% Data Sources
    MetaAPI[("Meta/Facebook API<br/>Campaign Data")]
    GHLAPI[("GoHighLevel API<br/>CRM Data")]
    
    %% Response
    Response[("📤 Response<br/>via GHL SMS/WhatsApp")]
    
    %% Flow connections
    User -->|"1. Request"| Security
    Security -->|"2. Validated"| Supervisor
    Security -.->|"Denied"| User
    
    Supervisor -->|"3a. Campaign Query"| MetaAgent
    Supervisor -->|"3b. CRM Operation"| GHLAgent
    
    MetaAgent -->|"4a. Fetch Data"| MetaAPI
    MetaAPI -->|"5a. Campaign Data"| MetaAgent
    
    GHLAgent -->|"4b. Execute"| GHLAPI
    GHLAPI -->|"5b. CRM Data"| GHLAgent
    
    MetaAgent -->|"6a. Analysis Result"| Supervisor
    GHLAgent -->|"6b. Operation Result"| Supervisor
    
    Supervisor -->|"7. Send Response"| GHLAgent
    GHLAgent -->|"8. Deliver"| Response
    Response -->|"9. Final"| User
    
    %% Styling
    classDef security fill:#ff6b6b,stroke:#c92a2a,color:#fff
    classDef supervisor fill:#4c6ef5,stroke:#364fc7,color:#fff
    classDef meta fill:#7950f2,stroke:#5f3dc4,color:#fff
    classDef ghl fill:#20c997,stroke:#0ca678,color:#fff
    classDef data fill:#868e96,stroke:#495057,color:#fff
    classDef user fill:#fab005,stroke:#f59f00,color:#000
    
    class Security security
    class Supervisor supervisor
    class MetaAgent meta
    class GHLAgent ghl
    class MetaAPI,GHLAPI data
    class User,Response user
```

## Detailed Security Flow

```mermaid
graph LR
    subgraph "Security Validation Process"
        Phone[Phone Number] --> Check1{Authorized?}
        Check1 -->|No| Deny1[Access Denied]
        Check1 -->|Yes| Check2{Locked Out?}
        Check2 -->|Yes| Deny2[Account Locked]
        Check2 -->|No| Check3{Has Permission?}
        Check3 -->|No| Deny3[Permission Denied]
        Check3 -->|Yes| Check4{Rate Limit OK?}
        Check4 -->|No| Deny4[Rate Limited]
        Check4 -->|Yes| Allow[✅ Access Granted]
    end
    
    Allow --> Role[Assign Role & Context]
    Role --> NextAgent[Route to Agent]
```

## Meta Campaign Agent Flow

```mermaid
graph TD
    subgraph "Meta Campaign Analysis"
        Question[User Question] --> Detect[Detect Intent & Entities]
        Detect --> Plan[Plan SDK Queries]
        
        Plan --> Query1[Campaign Insights]
        Plan --> Query2[AdSet Performance]
        Plan --> Query3[Demographics]
        
        Query1 --> SDK1[Meta SDK Call]
        Query2 --> SDK2[Meta SDK Call]
        Query3 --> SDK3[Meta SDK Call]
        
        SDK1 --> Aggregate[Aggregate Data]
        SDK2 --> Aggregate
        SDK3 --> Aggregate
        
        Aggregate --> Analyze[AI Analysis]
        Analyze --> Generate[Generate Answer]
        Generate --> Format[Format Response]
    end
```

## Question Processing Flow

```mermaid
sequenceDiagram
    participant U as User
    participant S as Security
    participant SV as Supervisor
    participant M as Meta Agent
    participant G as GHL Agent
    participant API as APIs
    
    U->>S: "What's the CTR in Miami?"
    S->>S: Validate Phone
    S->>S: Check Permissions
    S->>SV: Authorized Request
    
    SV->>SV: Analyze Intent
    Note over SV: Detected: Campaign Metric Query
    
    SV->>M: Route to Meta Agent
    M->>M: Parse Question
    Note over M: Location: Miami<br/>Metric: CTR
    
    M->>API: Query AdSets (Miami)
    API-->>M: AdSet Data
    
    M->>M: Calculate Metrics
    M->>M: Generate Insights
    
    M-->>SV: "Miami CTR: 2.8%"
    SV->>G: Send Response
    G->>API: Send SMS/WhatsApp
    API-->>U: Message Delivered
```

## State Flow Through System

```mermaid
stateDiagram-v2
    [*] --> Initializing: User Request
    
    Initializing --> SecurityCheck: Start
    
    SecurityCheck --> Unauthorized: Failed
    SecurityCheck --> Authorized: Passed
    
    Unauthorized --> [*]: Access Denied
    
    Authorized --> IntentAnalysis: Analyze Request
    
    IntentAnalysis --> MetaProcessing: Campaign Query
    IntentAnalysis --> GHLProcessing: CRM Operation
    IntentAnalysis --> BothProcessing: Combined Request
    
    MetaProcessing --> DataFetching: Fetch Campaign Data
    GHLProcessing --> CRMOperation: Execute CRM Task
    BothProcessing --> ParallelProcess: Both Agents
    
    DataFetching --> Analysis: Analyze Data
    CRMOperation --> ResultProcessing: Process Result
    ParallelProcess --> Aggregation: Combine Results
    
    Analysis --> ResponseGeneration: Generate Answer
    ResultProcessing --> ResponseGeneration: Format Result
    Aggregation --> ResponseGeneration: Compile Response
    
    ResponseGeneration --> MessageDelivery: Send via GHL
    MessageDelivery --> [*]: Complete
```

## Data Flow for Campaign Analysis

```mermaid
graph LR
    subgraph "Input Processing"
        Q[Question] --> NLP[NLP Processing]
        NLP --> E[Entities<br/>• Location<br/>• Metric<br/>• Time Period]
    end
    
    subgraph "Query Building"
        E --> QB[Query Builder]
        QB --> SQL[SDK Query<br/>• Fields<br/>• Filters<br/>• Breakdowns]
    end
    
    subgraph "Data Fetching"
        SQL --> API[Meta API]
        API --> Raw[Raw Data]
    end
    
    subgraph "Processing"
        Raw --> Agg[Aggregation]
        Agg --> Calc[Calculations<br/>• CTR<br/>• ROAS<br/>• CPC]
    end
    
    subgraph "Response"
        Calc --> Fmt[Format]
        Fmt --> Ans[Answer]
    end
```

## Agent Communication Protocol

```mermaid
graph TD
    subgraph "Message Format"
        State["State Object<br/>─────────<br/>• messages[]<br/>• phone_number<br/>• user_role<br/>• permissions[]<br/>• current_request<br/>• intent<br/>• responses{}"]
    end
    
    subgraph "Agent Handoffs"
        Sup[Supervisor] -->|"State + Context"| Meta[Meta Agent]
        Sup -->|"State + Context"| GHL[GHL Agent]
        Meta -->|"Result + State"| Sup
        GHL -->|"Result + State"| Sup
    end
    
    subgraph "Security Context"
        Ctx["Security Context<br/>─────────<br/>• authenticated: true<br/>• phone: +1786xxx<br/>• role: admin<br/>• timestamp: ISO"]
    end
```

## Error Handling Flow

```mermaid
graph TB
    Operation[Operation] --> Try{Try}
    Try -->|Success| Continue[Continue Flow]
    Try -->|Error| Catch[Catch Error]
    
    Catch --> Log[Log Error]
    Log --> Classify{Error Type}
    
    Classify -->|Auth| AuthError[Return 401]
    Classify -->|Rate| RateError[Return 429]
    Classify -->|API| APIError[Retry 3x]
    Classify -->|Other| GenError[Return 500]
    
    APIError -->|Failed| Fallback[Fallback Response]
    
    AuthError --> User[Notify User]
    RateError --> User
    GenError --> User
    Fallback --> User
```

## Typical User Journey

```mermaid
journey
    title Ryan Castro Campaign Query Journey
    
    section Authentication
      Send Message: 5: User
      Validate Phone: 3: Security
      Check Permissions: 3: Security
      Grant Access: 5: Security
    
    section Query Processing
      Analyze Intent: 4: Supervisor
      Route to Meta: 5: Supervisor
      Parse Question: 4: Meta Agent
      Detect Entities: 4: Meta Agent
    
    section Data Fetching
      Build SDK Query: 3: Meta Agent
      Call Meta API: 2: API
      Receive Data: 4: API
      Process Results: 4: Meta Agent
    
    section Response
      Generate Answer: 5: Meta Agent
      Format Response: 5: Supervisor
      Send via GHL: 4: GHL Agent
      Receive Answer: 5: User
```

## System Components Interaction

```mermaid
graph TB
    subgraph "Frontend Layer"
        SMS[SMS/WhatsApp]
        Web[Web Interface]
    end
    
    subgraph "Security Layer"
        Auth[Authentication]
        Perm[Permissions]
        Rate[Rate Limiter]
        Audit[Audit Logger]
    end
    
    subgraph "Agent Layer"
        Sup2[Supervisor]
        Meta2[Meta Agent]
        GHL2[GHL Agent]
        Sec2[Security Agent]
    end
    
    subgraph "Tool Layer"
        SDK[Meta SDK Tools]
        MCP[GHL MCP Tools]
        AI[AI Models]
    end
    
    subgraph "Data Layer"
        MetaDB[(Meta Ads Data)]
        GHLDB[(GHL CRM Data)]
        Logs[(Audit Logs)]
    end
    
    SMS --> Auth
    Web --> Auth
    Auth --> Sup2
    Sup2 --> Meta2
    Sup2 --> GHL2
    Meta2 --> SDK
    GHL2 --> MCP
    Meta2 --> AI
    SDK --> MetaDB
    MCP --> GHLDB
    Audit --> Logs
```

This diagram shows the complete flow of the Meta Ryan system, from user request through security validation, agent routing, data processing, and response delivery.