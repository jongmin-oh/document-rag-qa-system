(() => {
  "use strict";

  const form = document.querySelector("#ask-form");
  if (!form) return;

  const question = document.querySelector("#question");
  const questionDialog = document.querySelector("#question-dialog");
  const dialogTitle = document.querySelector("#question-dialog-title");
  const dialogPanel = questionDialog.querySelector(".dialog-panel");
  const questionComposer = document.querySelector("#question-composer");
  const openQuestionButton = document.querySelector("#open-question-dialog");
  const closeQuestionButton = document.querySelector("#close-question-dialog");
  const charCount = document.querySelector("#char-count");
  const questionError = document.querySelector("#question-error");
  const submitButton = form.querySelector("button[type='submit']");
  const loading = document.querySelector("#loading");
  const loadingMessage = document.querySelector("#loading-message");
  const answerSection = document.querySelector("#answer-section");
  const answerCard = answerSection.querySelector(".answer-card");
  const answerStatus = document.querySelector("#answer-status");
  const answerQuestion = document.querySelector("#answer-question");
  const answerContent = document.querySelector("#answer-content");
  const refusalHelp = document.querySelector("#refusal-help");
  const answerMeta = document.querySelector("#answer-meta");
  const citationsSection = document.querySelector("#citations-section");
  const citationList = document.querySelector("#citation-list");
  const citationCount = document.querySelector("#citation-count");
  const errorState = document.querySelector("#error-state");
  const retryButton = document.querySelector("#retry-button");
  const copyButton = document.querySelector("#copy-answer");
  const toast = document.querySelector("#toast");
  const responseSection = document.querySelector("#response-section");
  const responseActions = document.querySelector("#response-actions");
  const askAnotherButton = document.querySelector("#ask-another-button");
  const feedbackPrompt = document.querySelector("#feedback-prompt");
  const feedbackForm = document.querySelector("#feedback-form");
  const feedbackComment = document.querySelector("#feedback-comment");
  const feedbackThanks = document.querySelector("#feedback-thanks");
  const apiUrl = document.body.dataset.apiUrl || "/ask";
  const feedbackUrl = document.body.dataset.feedbackUrl || "/feedback";

  let loadingTimer = null;
  let lastQuestion = "";
  let currentAnswer = "";
  let currentInteractionId = "";

  const loadingMessages = [
    "질문을 문서에 쓰인 표현으로 정리하고 있습니다.",
    "관련된 공식 문서와 근거를 찾고 있습니다.",
    "찾은 내용을 쉬운 말로 정리하고 있습니다.",
  ];

  const updateCount = () => {
    charCount.textContent = `${question.value.length} / 1000`;
    if (question.value.trim()) {
      question.setAttribute("aria-invalid", "false");
      questionError.textContent = "";
    }
  };

  const setLoading = (active) => {
    loading.hidden = !active;
    submitButton.disabled = active;
    openQuestionButton.disabled = active;
    question.disabled = active;
    if (!active) {
      window.clearInterval(loadingTimer);
      loadingTimer = null;
      loadingMessage.textContent = loadingMessages[0];
      return;
    }

    let index = 0;
    loadingTimer = window.setInterval(() => {
      index = (index + 1) % loadingMessages.length;
      loadingMessage.textContent = loadingMessages[index];
    }, 2600);
  };

  const showToast = (message) => {
    toast.textContent = message;
    toast.hidden = false;
    window.setTimeout(() => { toast.hidden = true; }, 2200);
  };

  const splitSource = (source) => {
    const match = source.match(/^\[(.+?)\s*\|\s*(.+?)\s*기준\]\s*(.*)$/);
    if (!match) return { publisher: "공식 문서", date: "", path: source };
    return { publisher: match[1], date: match[2], path: match[3] };
  };

  const documentTitle = (publisher) => {
    if (publisher.includes("생활법령")) return "찾기 쉬운 생활법령정보 「실업급여」";
    if (publisher.includes("취업드림")) return "취업드림수첩";
    return publisher;
  };

  const pageLabel = (citation) => {
    if (citation.page_start === citation.page_end) return `${citation.page_start}쪽`;
    return `${citation.page_start}–${citation.page_end}쪽`;
  };

  const renderParagraphs = (text) => {
    answerContent.replaceChildren();
    const parts = text.split(/\n+/).map((part) => part.trim()).filter(Boolean);
    (parts.length ? parts : [text]).forEach((part) => {
      const paragraph = document.createElement("p");
      paragraph.textContent = part;
      answerContent.append(paragraph);
    });
  };

  const renderCitations = (citations) => {
    citationList.replaceChildren();
    citationCount.textContent = `${citations.length}개`;
    citationsSection.hidden = citations.length === 0;

    citations.forEach((citation, index) => {
      const parsed = splitSource(citation.source);
      const card = document.createElement("article");
      card.className = "citation-card";

      const number = document.createElement("span");
      number.className = "citation-number";
      number.textContent = `근거 ${index + 1}`;

      const body = document.createElement("div");
      body.className = "citation-body";

      const publisher = document.createElement("span");
      publisher.className = "citation-publisher";
      publisher.textContent = parsed.date ? `${parsed.publisher} · ${parsed.date} 기준` : parsed.publisher;

      const title = document.createElement("h4");
      title.textContent = documentTitle(parsed.publisher);

      const path = document.createElement("p");
      path.textContent = parsed.path || "관련 내용";

      const page = document.createElement("span");
      page.className = "citation-page";
      page.textContent = pageLabel(citation);

      body.append(publisher, title, path, page);
      card.append(number, body);
      citationList.append(card);
    });
  };

  const renderAnswer = (data) => {
    const answerable = Boolean(data.answerable);
    currentAnswer = data.answer || "";
    currentInteractionId = data.interaction_id || "";
    answerCard.classList.toggle("is-refusal", !answerable);
    answerStatus.className = `status-badge ${answerable ? "status-confirmed" : "status-unknown"}`;
    answerStatus.innerHTML = "";

    const statusIcon = document.createElement("span");
    statusIcon.setAttribute("aria-hidden", "true");
    statusIcon.textContent = answerable ? "✓" : "?";
    answerStatus.append(statusIcon, document.createTextNode(answerable ? " 자료에서 확인했어요" : " 현재 자료로 판단하기 어려워요"));

    answerQuestion.textContent = lastQuestion;
    renderParagraphs(currentAnswer);
    const citations = Array.isArray(data.citations) ? data.citations : [];
    renderCitations(citations);
    refusalHelp.hidden = answerable;
    copyButton.hidden = !answerable;
    answerMeta.hidden = citations.length === 0;
    answerMeta.textContent = "문서 기준일은 아래 근거 카드에서 확인할 수 있어요.";
    answerSection.hidden = false;
    answerSection.focus({ preventScroll: true });
    dialogPanel.scrollTop = 0;
  };

  const resetFeedback = () => {
    feedbackPrompt.hidden = false;
    feedbackForm.hidden = true;
    feedbackThanks.hidden = true;
    feedbackForm.reset();
  };

  const sendFeedback = async (rating, reason = null, comment = "") => {
    if (!currentInteractionId) {
      showToast("이 답변은 평가할 수 없어요.");
      return false;
    }

    const response = await fetch(feedbackUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        interaction_id: currentInteractionId,
        rating,
        reason,
        comment,
      }),
    });
    if (!response.ok) throw new Error(`feedback failed: ${response.status}`);
    feedbackPrompt.hidden = true;
    feedbackForm.hidden = true;
    feedbackThanks.hidden = false;
    return true;
  };

  const submitQuestion = async (text) => {
    const cleaned = text.trim();
    questionError.textContent = "";

    if (!cleaned) {
      questionError.textContent = "궁금한 내용을 한 문장 이상 입력해 주세요.";
      question.setAttribute("aria-invalid", "true");
      question.focus();
      return;
    }

    question.setAttribute("aria-invalid", "false");

    lastQuestion = cleaned;
    dialogTitle.textContent = "답변을 준비하고 있어요";
    questionComposer.hidden = true;
    responseSection.hidden = false;
    responseActions.hidden = true;
    resetFeedback();
    answerSection.hidden = true;
    errorState.hidden = true;
    setLoading(true);
    dialogPanel.scrollTop = 0;

    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: cleaned }),
      });

      if (!response.ok) throw new Error(`request failed: ${response.status}`);
      const data = await response.json();
      renderAnswer(data);
    } catch (error) {
      console.error(error);
      errorState.hidden = false;
    } finally {
      setLoading(false);
      dialogTitle.textContent = "질문 결과";
      responseActions.hidden = false;
    }
  };

  question.addEventListener("input", updateCount);

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    submitQuestion(question.value);
  });

  openQuestionButton.addEventListener("click", () => {
    questionDialog.showModal();
    question.focus();
  });

  closeQuestionButton.addEventListener("click", () => questionDialog.close());

  questionDialog.addEventListener("click", (event) => {
    if (event.target === questionDialog) questionDialog.close();
  });

  document.querySelectorAll(".example-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      question.value = chip.textContent.trim();
      updateCount();
      submitQuestion(question.value);
    });
  });

  retryButton.addEventListener("click", () => submitQuestion(lastQuestion));

  askAnotherButton.addEventListener("click", () => {
    responseSection.hidden = true;
    answerSection.hidden = true;
    errorState.hidden = true;
    responseActions.hidden = true;
    questionComposer.hidden = false;
    dialogTitle.textContent = "어떤 점이 궁금하신가요?";
    dialogPanel.scrollTop = 0;
    question.focus();
    question.select();
  });

  document.querySelectorAll(".feedback-rating").forEach((button) => {
    button.addEventListener("click", async () => {
      const rating = button.dataset.rating;
      if (rating === "not_helpful") {
        feedbackPrompt.hidden = true;
        feedbackForm.hidden = false;
        feedbackForm.querySelector("input").focus();
        return;
      }
      try {
        await sendFeedback(rating);
      } catch (error) {
        console.error(error);
        showToast("평가를 저장하지 못했어요. 잠시 후 다시 시도해 주세요.");
      }
    });
  });

  feedbackForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const reason = new FormData(feedbackForm).get("feedback-reason");
    if (!reason) return;
    const button = feedbackForm.querySelector("button[type='submit']");
    button.disabled = true;
    try {
      await sendFeedback("not_helpful", reason, feedbackComment.value);
    } catch (error) {
      console.error(error);
      showToast("의견을 저장하지 못했어요. 잠시 후 다시 시도해 주세요.");
    } finally {
      button.disabled = false;
    }
  });

  copyButton.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(currentAnswer);
      showToast("답변을 복사했어요.");
    } catch {
      showToast("복사하지 못했어요. 답변을 직접 선택해 주세요.");
    }
  });

  updateCount();
  resetFeedback();
})();
