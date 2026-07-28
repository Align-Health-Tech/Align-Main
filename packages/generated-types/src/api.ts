// Generated from apps/api-server FastAPI OpenAPI. Do not edit.
export interface paths {
    "/sessions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Create Session
         * @description Create guest encounter at NOT_STARTED; return consent NextStep.
         *
         *     Optional query params are M6/dev helpers (CLI / tests). Production QR
         *     binding will set org + language without a body (APISTRUCTURE).
         */
        post: operations["create_session_sessions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/sessions/{session_id}/respond": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Respond */
        post: operations["respond_sessions__session_id__respond_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/sessions/{session_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Session */
        get: operations["get_session_sessions__session_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/clinician/sessions/{session_id}/complete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Mark Complete
         * @description AWAITING_REVIEW → COMPLETED. 409 otherwise.
         */
        post: operations["mark_complete_clinician_sessions__session_id__complete_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Health
         * @description Confirms the process is up and (separately) that DATABASE_URL
         *     resolves — doesn't check the DB connection itself yet.
         */
        get: operations["health_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** CompleteResponse */
        CompleteResponse: {
            /** Session Id */
            session_id: string;
            /** Status */
            status: string;
        };
        /** CreateSessionResponse */
        CreateSessionResponse: {
            /** Session Id */
            session_id: string;
            next_step: components["schemas"]["NextStep"];
            /** Status */
            status: string;
        };
        /** GetSessionResponse */
        GetSessionResponse: {
            next_step: components["schemas"]["NextStep"];
            /** Status */
            status: string;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** NextStep */
        NextStep: {
            /**
             * Step Type
             * @enum {string}
             */
            step_type: "consent" | "question_batch" | "body_diagram" | "survey" | "complete";
            /**
             * Phase
             * @enum {string}
             */
            phase: "consent" | "presenting_complaint" | "localised_detail" | "non_localised_detail" | "priority_questions" | "redflag_screening" | "optional_questions" | "ice" | "survey";
            /** Turn Number */
            turn_number: number;
            /** Questions */
            questions?: components["schemas"]["QuestionField"][] | null;
            /** Diagram File */
            diagram_file?: string | null;
            /** Highlighted Region Ids */
            highlighted_region_ids?: string[] | null;
        };
        /** QuestionField */
        QuestionField: {
            /** Id */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "single_choice" | "multi_choice" | "yes_no" | "consent_accept" | "free_text";
            /** Prompt */
            prompt: string;
            /** En Prompt */
            en_prompt?: string | null;
            /** Options */
            options?: components["schemas"]["QuestionOption"][] | null;
            /**
             * Required
             * @default true
             */
            required: boolean;
            /** Default Value */
            default_value?: string | null;
            /** Default Values */
            default_values?: string[] | null;
            /** Collect Target Id */
            collect_target_id?: string | null;
            /** Personalization Note */
            personalization_note: string;
        };
        /** QuestionOption */
        QuestionOption: {
            /** Value */
            value: string;
            /** Label */
            label: string;
            /** En Label */
            en_label?: string | null;
        };
        /** RespondRequest */
        RespondRequest: {
            /**
             * Answer
             * @description Shape depends on current step_type (consent / batch / diagram / survey)
             */
            answer: {
                [key: string]: unknown;
            };
        };
        /** RespondResponse */
        RespondResponse: {
            next_step: components["schemas"]["NextStep"];
            /** Status */
            status: string;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    create_session_sessions_post: {
        parameters: {
            query?: {
                session_language?: string | null;
                patient_sex?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CreateSessionResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    respond_sessions__session_id__respond_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RespondRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RespondResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_session_sessions__session_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GetSessionResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    mark_complete_clinician_sessions__session_id__complete_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CompleteResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    health_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
        };
    };
}
