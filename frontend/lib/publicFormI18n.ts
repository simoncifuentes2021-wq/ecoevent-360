export type PublicFormLanguage = "es" | "en" | "pt" | "ko";

type PublicFormCopy = {
  chooseLanguage: string;
  loadingForm: string;
  loadError: string;
  unavailableTitle: string;
  retry: string;
  inactive: string;
  notOpenYet: string;
  closed: string;
  notFound: string;
  unavailableDefault: string;
  submitError: string;
  successTitle: string;
  bikeZoneCode: string;
  bikeZoneInstruction: string;
  responseCode: string;
  submitting: string;
  selectPlaceholder: string;
  yes: string;
  no: string;
};

const COPY: Record<PublicFormLanguage, PublicFormCopy> = {
  es: {
    chooseLanguage: "Elige tu idioma para continuar",
    loadingForm: "Cargando formulario...",
    loadError: "No se pudo cargar el formulario.",
    unavailableTitle: "Formulario no disponible",
    retry: "Reintentar",
    inactive: "Este formulario no está abierto para recibir respuestas en este momento.",
    notOpenYet: "Este formulario todavía no está abierto. Intenta nuevamente cuando comience el periodo de respuestas.",
    closed: "Este formulario ya cerró y no acepta nuevas respuestas.",
    notFound: "El enlace no corresponde a un formulario público disponible.",
    unavailableDefault: "No pudimos cargar este formulario. Revisa el enlace o intenta nuevamente más tarde.",
    submitError: "No se pudo enviar el formulario.",
    successTitle: "Respuesta recibida",
    bikeZoneCode: "Código Bike Zone",
    bikeZoneInstruction: "Usa este código para check-in y check-out.",
    responseCode: "Código de respuesta",
    submitting: "Enviando...",
    selectPlaceholder: "Selecciona",
    yes: "Sí",
    no: "No",
  },
  en: {
    chooseLanguage: "Choose your language to continue",
    loadingForm: "Loading form...",
    loadError: "The form could not be loaded.",
    unavailableTitle: "Form unavailable",
    retry: "Try again",
    inactive: "This form is not currently open for responses.",
    notOpenYet: "This form is not open yet. Please try again when the response period begins.",
    closed: "This form is closed and no longer accepts responses.",
    notFound: "This link does not match an available public form.",
    unavailableDefault: "We could not load this form. Check the link or try again later.",
    submitError: "The form could not be submitted.",
    successTitle: "Response received",
    bikeZoneCode: "Bike Zone code",
    bikeZoneInstruction: "Use this code for check-in and check-out.",
    responseCode: "Response code",
    submitting: "Submitting...",
    selectPlaceholder: "Select",
    yes: "Yes",
    no: "No",
  },
  pt: {
    chooseLanguage: "Escolha seu idioma para continuar",
    loadingForm: "Carregando formulário...",
    loadError: "Não foi possível carregar o formulário.",
    unavailableTitle: "Formulário indisponível",
    retry: "Tentar novamente",
    inactive: "Este formulário não está aberto para receber respostas neste momento.",
    notOpenYet: "Este formulário ainda não está aberto. Tente novamente quando o período de respostas começar.",
    closed: "Este formulário foi encerrado e não aceita novas respostas.",
    notFound: "O link não corresponde a um formulário público disponível.",
    unavailableDefault: "Não foi possível carregar este formulário. Verifique o link ou tente novamente mais tarde.",
    submitError: "Não foi possível enviar o formulário.",
    successTitle: "Resposta recebida",
    bikeZoneCode: "Código Bike Zone",
    bikeZoneInstruction: "Use este código para check-in e check-out.",
    responseCode: "Código da resposta",
    submitting: "Enviando...",
    selectPlaceholder: "Selecione",
    yes: "Sim",
    no: "Não",
  },
  ko: {
    chooseLanguage: "계속하려면 언어를 선택하세요",
    loadingForm: "양식을 불러오는 중...",
    loadError: "양식을 불러올 수 없습니다.",
    unavailableTitle: "양식을 사용할 수 없습니다",
    retry: "다시 시도",
    inactive: "현재 이 양식은 응답을 받고 있지 않습니다.",
    notOpenYet: "아직 이 양식의 응답 기간이 시작되지 않았습니다. 응답 기간이 시작되면 다시 시도하세요.",
    closed: "이 양식은 마감되어 더 이상 응답을 받지 않습니다.",
    notFound: "이 링크에 해당하는 공개 양식을 찾을 수 없습니다.",
    unavailableDefault: "양식을 불러올 수 없습니다. 링크를 확인하거나 나중에 다시 시도하세요.",
    submitError: "양식을 제출할 수 없습니다.",
    successTitle: "응답이 접수되었습니다",
    bikeZoneCode: "Bike Zone 코드",
    bikeZoneInstruction: "체크인 및 체크아웃 시 이 코드를 사용하세요.",
    responseCode: "응답 코드",
    submitting: "제출 중...",
    selectPlaceholder: "선택하세요",
    yes: "예",
    no: "아니요",
  },
};

export function normalizePublicFormLanguage(language?: string | null): PublicFormLanguage {
  return language === "en" || language === "pt" || language === "ko" ? language : "es";
}

export function publicFormCopy(language?: string | null): PublicFormCopy {
  return COPY[normalizePublicFormLanguage(language)];
}
