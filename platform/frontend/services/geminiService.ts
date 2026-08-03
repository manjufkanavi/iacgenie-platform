import { CloudProvider, ClarifyAnswerResponse, GenerationStartResponse, GenerationStatusResponse } from '../types';

const getToken = () => localStorage.getItem('iacgenie_token');

/**
 * Sends a request to start the code generation process on the backend.
 * @param prompt The user's prompt.
 * @param model The selected AI model.
 * @param provider The selected cloud provider.
 * @returns A promise that resolves with an object containing the job_id.
 */
export const startGeneration = async (
  prompt: string,
  model: string,
  provider: CloudProvider,
  projectId?: string,
  baseJobId?: string,
  modelConfigId?: string
): Promise<GenerationStartResponse> => {
  const requestBody = { prompt, model, provider, project_id: projectId, base_job_id: baseJobId, model_config_id: modelConfigId };
  console.log('Sending generation request to /api/workflow/start with payload:', requestBody);

  try {
    const token = getToken();
    const response = await fetch('/api/workflow/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
        let errorBodyText = await response.text();
        try {
            const errorJson = JSON.parse(errorBodyText);
            if (typeof errorJson.detail === 'string') {
                errorBodyText = errorJson.detail;
            } else if (errorJson.detail && errorJson.detail.message) {
                errorBodyText = errorJson.detail.message;
            } else if (errorJson.error && typeof errorJson.error === 'string') {
                errorBodyText = errorJson.error;
            } else if (errorJson.error && errorJson.error.message) {
                errorBodyText = errorJson.error.message;
            } else if (errorJson.message) {
                errorBodyText = errorJson.message;
            } else {
                errorBodyText = JSON.stringify(errorJson);
            }
        } catch {}
        throw new Error(`Failed to start generation session. ${errorBodyText}`);
    }

    const responseData = await response.json();
    // /api/workflow/start returns { success, data: { id, status, user_id } }
    // Extract session_id from data.id (build_id = session_id)
    const sessionId = responseData?.data?.id || responseData?.data?.build_id;
    if (sessionId) {
        return { job_id: sessionId, session_id: sessionId };
    } else {
        throw new Error("Invalid response from server when starting session.");
    }
  } catch (error) {
    console.error('Error during startGeneration fetch:', error);
    if (error instanceof Error) {
        throw error;
    }
    throw new Error('An unknown error occurred while starting the generation session.');
  }
};

/**
 * Polls the backend for the status of a specific generation job.
 * @param jobId The ID of the job to poll.
 * @returns A promise that resolves with the full status response from the backend.
 */
export const pollGenerationStatus = async (jobId: string): Promise<GenerationStatusResponse> => {
    try {
        const token = getToken();
        // Use the generation status endpoint which returns job_id, status, logs, and code
        const response = await fetch(`/api/generate/status/${jobId}`, {
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });

        if (!response.ok) {
             throw new Error(`Failed to poll job status for job ID ${jobId}. Server responded with ${response.status}`);
        }

        const data = await response.json();
        // /api/generate/status/{jobId} returns { job_id, status, logs, code }
        if (data && data.job_id) {
            return data as GenerationStatusResponse;
        } else {
            throw new Error('Invalid status response structure from server.');
        }

    } catch (error) {
        console.error(`Error polling status for job ${jobId}:`, error); // nosemgrep: javascript.lang.security.audit.unsafe-formatstring.unsafe-formatstring
        if (error instanceof Error) {
            throw error;
        }
        throw new Error('An unknown error occurred during status polling.');
    }
}


/**
 * Deploy the generated infrastructure using OpenTofu.
 * @param jobId The ID of the generation job.
 * @param projectName The name for the project.
 * @returns A promise that resolves with deployment status.
 */
export const deployInfrastructure = async (jobId: string, projectName: string): Promise<any> => {
    try {
        const response = await fetch('/api/deploy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_id: jobId, project_name: projectName }),
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Deployment failed: ${errorText}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error during deployment:', error);
        if (error instanceof Error) {
            throw error;
        }
        throw new Error('An unknown error occurred during deployment.');
    }
};

/**
 * Push generated code to GitHub.
 * @param jobId The ID of the generation job.
 * @param repoName The name for the GitHub repository.
 * @param description The repository description.
 * @returns A promise that resolves with GitHub push status.
 */
export const pushToGitHub = async (jobId: string, repoName: string, description: string): Promise<any> => {
    try {
        const response = await fetch('/api/github', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                job_id: jobId, 
                repo_name: repoName, 
                description: description 
            }),
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`GitHub push failed: ${errorText}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error during GitHub push:', error);
        if (error instanceof Error) {
            throw error;
        }
        throw new Error('An unknown error occurred during GitHub push.');
    }
};

/**
 * Download the generated project as a ZIP file.
 * @param jobId The ID of the generation job.
 * @returns A promise that resolves with the download URL.
 */
export const downloadProject = async (jobId: string): Promise<void> => {
    try {
        const response = await fetch(`/api/download/${jobId}`);

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Download failed: ${errorText}`);
        }

        // Create blob and download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `iacgenie-project-${jobId.slice(0, 8)}.zip`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Error during download:', error);
        if (error instanceof Error) {
            throw error;
        }
        throw new Error('An unknown error occurred during download.');
    }
};

/**
 * Get logs for a specific job.
 * @param jobId The ID of the job.
 * @returns A promise that resolves with the job logs.
 */
export const getJobLogs = async (jobId: string): Promise<any> => {
    try {
        const response = await fetch(`/api/logs/${jobId}`);

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to get logs: ${errorText}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Error getting job logs:', error);
        if (error instanceof Error) {
            throw error;
        }
        throw new Error('An unknown error occurred while getting logs.');
    }
};

/**
 * Submit answers to clarification questions and get the next round of questions or proceed to generation.
 * @param jobId The ID of the clarification job.
 * @param message The user's conversational reply.
 * @returns A promise that resolves with clarification results (more questions or refined spec).
 */
export const submitClarifyAnswer = async (
  jobId: string,
  message?: string,
  selectedOptionValue?: string
): Promise<ClarifyAnswerResponse> => {
  const token = getToken();
  try {
    const response = await fetch('/api/clarify/answer', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ job_id: jobId, message, selected_option_value: selectedOptionValue }),
    });

    if (!response.ok) {
      let errorBodyText = await response.text();
      try {
        const errorJson = JSON.parse(errorBodyText);
        if (typeof errorJson.detail === 'string') {
            errorBodyText = errorJson.detail;
        } else if (errorJson.detail && errorJson.detail.message) {
            errorBodyText = errorJson.detail.message;
        } else if (errorJson.error && typeof errorJson.error === 'string') {
            errorBodyText = errorJson.error;
        } else if (errorJson.error && errorJson.error.message) {
            errorBodyText = errorJson.error.message;
        } else if (errorJson.message) {
            errorBodyText = errorJson.message;
        } else {
            errorBodyText = JSON.stringify(errorJson);
        }
      } catch {}
      throw new Error(`Failed to submit clarification answer: ${errorBodyText}`);
    }

    const data = await response.json();
    // Response wraps data in { success, data, message } pattern
    const payload = data.data || data;
    if (!payload.status) {
      throw new Error('Invalid clarification response structure from server.');
    }
    return payload as ClarifyAnswerResponse;

  } catch (error) {
    console.error('Error submitting clarification answer:', error);
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('An unknown error occurred while submitting clarification answer.');
  }
};