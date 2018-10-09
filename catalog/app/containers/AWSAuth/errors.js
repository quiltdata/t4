import { BaseError } from 'utils/error';

const withDefaultMessage = (message, props) => ({ message, ...props });

export class AWSAuthError extends BaseError {
  static displayName = 'AWSAuthError';

  constructor(props) {
    const { message, ...rest } = withDefaultMessage('auth error', props);
    super(message, rest);
  }
}

export class InvalidCredentials extends AWSAuthError {
  static displayName = 'InvalidCredentials';

  constructor(props) {
    super(withDefaultMessage('invalid credentials', props));
  }
}
