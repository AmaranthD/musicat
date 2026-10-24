let client = null;
let handlers = { onSignedIn: () => {}, onSignedOut: () => {} };
let mode = "signin";
let wired = false;
let currentUser = null;
let repairMode = false;

const ERROR_TRANSLATIONS = [
  ["Invalid login credentials", "E-mail ou senha incorretos."],
  ["Email not confirmed", "Confirme seu e-mail antes de entrar."],
  ["User already registered", "Este e-mail já tem uma conta."],
  ["Password should be at least", "A senha precisa ter pelo menos 6 caracteres."],
  ["Signups not allowed", "O cadastro está desativado neste projeto."],
  ["Unable to validate email address", "E-mail inválido."],
  ["For security purposes", "Muitas tentativas. Aguarde alguns segundos e tente de novo."],
];

function translate(message) {
  const found = ERROR_TRANSLATIONS.find(([needle]) => message.includes(needle));
  return found ? found[1] : message;
}

function el(id) {
  return document.getElementById(id);
}

function showGate() {
  document.body.classList.remove("is-authenticated");
  el("account").hidden = true;
  el("auth-gate").hidden = false;
  el("auth-email").focus();
}

function hideGate() {
  document.body.classList.add("is-authenticated");
  el("auth-gate").hidden = true;
  el("account").hidden = false;
}

function setMode(next) {
  mode = next;
  repairMode = false;
  el("auth-tabs").hidden = false;
  el("auth-email-label").hidden = false;
  el("auth-forgot").hidden = false;
  for (const tab of el("auth-tabs").querySelectorAll("[data-mode]")) {
    tab.classList.toggle("is-active", tab.dataset.mode === mode);
  }
  el("auth-submit").textContent = mode === "signin" ? "Entrar" : "Criar conta";
  el("auth-password").autocomplete =
    mode === "signin" ? "current-password" : "new-password";
  feedback("", false);
}

function enterRecoveryMode() {
  mode = "recovery";
  repairMode = true;
  el("auth-tabs").hidden = true;
  el("auth-email-label").hidden = true;
  el("auth-forgot").hidden = true;
  el("auth-submit").textContent = "Salvar nova senha";
  el("auth-password").value = "";
  el("auth-password").autocomplete = "new-password";
  feedback("Escolha uma nova senha para sua conta.", false);
  showGate();
}

function feedback(message, isError = true) {
  const node = el("auth-feedback");
  node.textContent = message;
  node.hidden = !message;
  node.classList.toggle("is-error", Boolean(message) && isError);
  node.classList.toggle("is-info", Boolean(message) && !isError);
}

async function syncCookie(session) {
  if (!session) return;
  try {
    await fetch("/api/auth/session", {
      method: "POST",
      headers: { Authorization: `Bearer ${session.access_token}` },
    });
  } catch (error) {
    /* a mídia continua funcionando via Bearer nos endpoints JSON */
  }
}

async function handleSession(session) {
  if (!session) {
    currentUser = null;
    showGate();
    return;
  }
  if (repairMode) {
    currentUser = session.user;
    showGate();
    return;
  }
  currentUser = session.user;
  await syncCookie(session);
  if (window.location.hash.includes("access_token")) {
    history.replaceState(null, "", window.location.pathname);
  }
  el("account-email").textContent = session.user?.email || "conta";
  hideGate();
  await handlers.onSignedIn(session.user);
}

function wire() {
  if (wired) return;
  wired = true;

  for (const tab of el("auth-tabs").querySelectorAll("[data-mode]")) {
    tab.addEventListener("click", () => setMode(tab.dataset.mode));
  }

  el("auth-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = el("auth-email").value.trim();
    const password = el("auth-password").value;
    if (mode !== "recovery" && !email) {
      feedback("Informe seu e-mail.");
      return;
    }
    if (password.length < 6) {
      feedback("A senha precisa ter pelo menos 6 caracteres.");
      return;
    }
    el("auth-submit").disabled = true;
    feedback("");
    try {
      if (mode === "recovery") {
        const { error } = await client.auth.updateUser({ password });
        if (error) {
          feedback(translate(error.message));
        } else {
          feedback("Senha atualizada.", false);
          history.replaceState(null, "", window.location.pathname);
          repairMode = false;
          const { data } = await client.auth.getSession();
          await handleSession(data.session);
        }
      } else if (mode === "signin") {
        const { error } = await client.auth.signInWithPassword({ email, password });
        if (error) feedback(translate(error.message));
      } else {
        const { data, error } = await client.auth.signUp({
          email,
          password,
          options: { emailRedirectTo: window.location.origin },
        });
        if (error) {
          feedback(translate(error.message));
        } else if (!data.session) {
          feedback(
            "Conta criada. Confirme o e-mail enviado para entrar. " +
              "Se não encontrar, verifique a caixa de spam.",
            false,
          );
        }
      }
    } catch (error) {
      feedback("Não foi possível conectar ao serviço de login.");
    } finally {
      el("auth-submit").disabled = false;
    }
  });

  el("auth-forgot").addEventListener("click", async () => {
    const email = el("auth-email").value.trim();
    if (!email) {
      feedback("Informe seu e-mail para recuperar a senha.");
      el("auth-email").focus();
      return;
    }
    const { error } = await client.auth.resetPasswordForEmail(email, {
      redirectTo: window.location.origin,
    });
    if (error) {
      feedback(translate(error.message));
    } else {
      feedback(
        "Se este e-mail existir, enviamos um link para redefinir a senha.",
        false,
      );
    }
  });

  el("logout").addEventListener("click", async () => {
    try {
      await fetch("/api/auth/session", { method: "DELETE" });
    } catch (error) {
      /* ignore */
    }
    await client.auth.signOut();
  });
}

export async function initAuth(handlersInput) {
  handlers = { ...handlers, ...handlersInput };
  el("auth-gate").hidden = false;
  feedback("", false);

  let config;
  try {
    const response = await fetch("/api/auth/config");
    config = await response.json();
  } catch (error) {
    feedback("Não foi possível carregar a configuração de login.");
    return;
  }

  if (!window.supabase) {
    feedback("A biblioteca de login não carregou. Recarregue a página.");
    return;
  }

  client = window.supabase.createClient(config.supabase_url, config.supabase_key, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  });

  wire();
  setMode("signin");

  const recovering =
    window.location.hash.includes("type=recovery") ||
    window.location.search.includes("type=recovery");
  const { data } = await client.auth.getSession();
  if (recovering && data.session) {
    enterRecoveryMode();
  } else {
    await handleSession(data.session);
  }

  client.auth.onAuthStateChange((event, session) => {
    setTimeout(async () => {
      if (event === "PASSWORD_RECOVERY") {
        enterRecoveryMode();
      } else if (event === "SIGNED_OUT") {
        currentUser = null;
        setMode("signin");
        handlers.onSignedOut();
        showGate();
      } else if (event === "SIGNED_IN") {
        if (repairMode) {
          enterRecoveryMode();
        } else if (session && currentUser?.id !== session.user?.id) {
          await handleSession(session);
        }
      } else if (event === "TOKEN_REFRESHED" && session) {
        await syncCookie(session);
      }
    }, 0);
  });
}

export async function apiFetch(path, options = {}) {
  if (!client) throw new Error("auth não inicializada");
  const { data } = await client.auth.getSession();
  let session = data.session;
  if (!session) {
    showGate();
    return new Response(null, { status: 401 });
  }

  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${session.access_token}`);
  let response = await fetch(path, { ...options, headers });

  if (response.status === 401) {
    const { data: refreshed } = await client.auth.refreshSession();
    if (refreshed.session) {
      headers.set("Authorization", `Bearer ${refreshed.session.access_token}`);
      response = await fetch(path, { ...options, headers });
    } else {
      await client.auth.signOut();
    }
  }
  return response;
}
